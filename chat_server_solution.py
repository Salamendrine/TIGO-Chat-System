# uncompyle6 version 3.1.3
# Python bytecode 3.6 (3379)
# Decompiled from: Python 3.6.3 |Anaconda, Inc.| (default, Oct  6 2017, 12:04:38)
# [GCC 4.2.1 Compatible Clang 4.0.1 (tags/RELEASE_401/final)]
# Embedded file name: chat_server.py
# Compiled at: 2018-04-11 16:17:43
# Size of source mod 2**32: 9496 bytes
"""
Created on Tue Jul 22 00:47:05 2014

@author: alina, zzhang
"""
import time
import socket
import select
import sys
import string
import indexer
import json
import pickle as pkl
from chat_utils import *
import chat_group as grp


class Server:

    def __init__(self):
        self.new_clients = []
        self.logged_name2sock = {}
        self.logged_sock2name = {}
        self.all_sockets = []
        self.group = grp.Group()
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.bind(SERVER)
        self.server.listen(5)
        self.all_sockets.append(self.server)
        self.indices = {}
        self.sonnet_f = open('AllSonnets.txt.idx', 'rb')
        self.sonnet = pkl.load(self.sonnet_f)
        self.sonnet_f.close()
        self.mute_list = list()

    def new_client(self, sock):
        print('new client...')
        sock.setblocking(0)
        self.new_clients.append(sock)
        self.all_sockets.append(sock)

    def login(self, sock):
        try:
            msg = json.loads(myrecv(sock))
            if len(msg) > 0:
                if msg['action'] == 'login':
                    name = msg['name']
                    if self.group.is_member(name) != True:
                        self.new_clients.remove(sock)
                        self.logged_name2sock[name] = sock
                        self.logged_sock2name[sock] = name
                        if name not in self.indices.keys():
                            try:
                                self.indices[name] = pkl.load(open(name + '.idx', 'rb'))
                            except IOError:
                                self.indices[name] = indexer.Index(name)

                            print(name + ' logged in')
                            self.group.join(name)
                            mysend(sock, json.dumps({'action': 'login', 'status': 'ok'}))
                        else:
                            mysend(sock, json.dumps({'action': 'login', 'status': 'duplicate'}))
                            print(name + ' duplicate login attempt')
                    else:
                        print('wrong code received')
                else:
                    self.logout(sock)
        except:
            self.all_sockets.remove(sock)

    def logout(self, sock):
        name = self.logged_sock2name[sock]
        pkl.dump(self.indices[name], open(name + '.idx', 'wb'))
        del self.indices[name]
        del self.logged_name2sock[name]
        del self.logged_sock2name[sock]
        self.all_sockets.remove(sock)
        self.group.leave(name)
        sock.close()

    def handle_msg(self, from_sock):
        msg = myrecv(from_sock)
        if len(msg) > 0:
            msg = json.loads(msg)
            if msg['action'] == 'connect':
                to_name = msg['target']
                from_name = self.logged_sock2name[from_sock]
                if to_name == from_name:
                    msg = json.dumps({'action': 'connect', 'status': 'self'})
                else:
                    if self.group.is_member(to_name):
                        to_sock = self.logged_name2sock[to_name]
                        self.group.connect(from_name, to_name)
                        the_guys = self.group.list_me(from_name)
                        msg = json.dumps({'action': 'connect', 'status': 'success'})
                        for g in the_guys[1:]:
                            to_sock = self.logged_name2sock[g]
                            mysend(to_sock, json.dumps({'action': 'connect', 'status': 'request', 'from': from_name}))

                    else:
                        msg = json.dumps({'action': 'connect', 'status': 'no-user'})
                    mysend(from_sock, msg)
            elif msg['action'] == 'exchange':
                from_name = self.logged_sock2name[from_sock]
                the_guys = self.group.list_me(from_name)

                message = msg['message']

                said2 = text_proc(msg['message'], from_name)
                self.indices[from_name].add_msg_and_index(said2)

                if from_name not in self.mute_list:

                    if message[:5] == 'mute ':
                        muted_guy = message[5:]
                        self.mute_list.append(muted_guy)

                        for g in the_guys[1:]:
                            to_sock = self.logged_name2sock[g]
                            self.indices[g].add_msg_and_index(said2)
                            mysend(to_sock, json.dumps({'action': 'exchange', 'from': msg['from'], 'message': 'Admin has muted {}'.format(muted_guy)}))

                    elif message[:7] == 'unmute ':
                        unmuted_guy = message[7:]
                        self.mute_list.pop(unmuted_guy)

                        for g in the_guys[1:]:
                            to_sock = self.logged_name2sock[g]
                            self.indices[g].add_msg_and_index(said2)
                            mysend(to_sock, json.dumps({'action': 'exchange', 'from': msg['from'], 'message': 'Admin has unmuted {}'.format(muted_guy)}))

                    else:
                        for g in the_guys[1:]:
                            to_sock = self.logged_name2sock[g]
                            self.indices[g].add_msg_and_index(said2)
                            mysend(to_sock, json.dumps({'action': 'exchange', 'from': msg['from'], 'message': message}))

                else:
                    to_sock = self.logged_name2sock[from_name]
                    mysend(to_sock, json.dumps({'action': 'exchange', 'from': msg['from'], 'message': "You are muted!\nNot sent!"}))

            elif msg['action'] == 'list':
                from_name = self.logged_sock2name[from_sock]
                msg = self.group.list_all(from_name)
                mysend(from_sock, json.dumps({'action': 'list', 'results': msg}))

            elif msg['action'] == 'poem':
                poem_indx = int(msg['target'])
                from_name = self.logged_sock2name[from_sock]
                print(from_name + ' asks for ', poem_indx)
                poem = self.sonnet.get_sect(poem_indx)
                print('here:\n', poem)
                mysend(from_sock, json.dumps({'action': 'poem', 'results': poem}))

            else:
                if msg['action'] == 'time':
                    ctime = time.strftime('%d.%m.%y,%H:%M', time.localtime())
                    mysend(from_sock, json.dumps({'action': 'time', 'results': ctime}))
                else:
                    if msg['action'] == 'search':
                        term = msg['target']
                        from_name = self.logged_sock2name[from_sock]
                        print('search for ' + from_name + ' for ' + term)
                        search_rslt = self.indices[from_name].search(term).strip()
                        print('server side search: ' + search_rslt)
                        mysend(from_sock, json.dumps({'action': 'search', 'results': search_rslt}))
                    else:
                        if msg['action'] == 'disconnect':
                            from_name = self.logged_sock2name[from_sock]
                            the_guys = self.group.list_me(from_name)
                            self.group.disconnect(from_name)
                            the_guys.remove(from_name)
                            if len(the_guys) == 1:
                                g = the_guys.pop()
                                to_sock = self.logged_name2sock[g]
                                mysend(to_sock, json.dumps({'action': 'disconnect'}))
        else:
            self.logout(from_sock)

    def run(self):
        print('starting server...')
        while 1:
            read, write, error = select.select(self.all_sockets, [], [])
            print('checking logged clients..')
            for logc in list(self.logged_name2sock.values()):
                if logc in read:
                    self.handle_msg(logc)

            print('checking new clients..')
            for newc in self.new_clients[:]:
                if newc in read:
                    self.login(newc)

            print('checking for new connections..')
            if self.server in read:
                sock, address = self.server.accept()
                self.new_client(sock)


def main():
    server = Server()
    server.run()


main()
# okay decompiling chat_server.cpython-36.pyc
