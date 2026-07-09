#ifndef SOCKET_H
#define SOCKET_H

#define _WIN32_WINNT 0x0600
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <winsock2.h>
#include <string>

class Socket
{
private:
    WSADATA wsaData;
    SOCKET sock;
    sockaddr_in serverAddr;

public:
    Socket(int port, const std::string &ip);
    void send(const std::string &message);
};

#endif