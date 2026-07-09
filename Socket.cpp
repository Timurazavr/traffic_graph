#include "socket.h"
#include <ws2tcpip.h>
#include <iostream>

#pragma comment(lib, "ws2_32.lib")

Socket::Socket(int port, const std::string &ip) : sock(INVALID_SOCKET)
{
    if (WSAStartup(MAKEWORD(2, 2), &wsaData) != 0)
    {
        std::cerr << "WSAStartup failed" << std::endl;
        exit(1);
    }

    sock = socket(AF_INET, SOCK_DGRAM, 0);
    if (sock == INVALID_SOCKET)
    {
        std::cerr << "Socket creation failed" << std::endl;
        exit(1);
    }

    serverAddr.sin_family = AF_INET;
    serverAddr.sin_port = htons(port);

    if (inet_pton(AF_INET, ip.c_str(), &serverAddr.sin_addr) <= 0)
    {
        std::cerr << "Invalid IP address format!" << std::endl;
        exit(1);
    }
}

void Socket::send(const std::string &message)
{
    int result = sendto(sock, message.c_str(), (int)message.size(), 0, (sockaddr *)&serverAddr, sizeof(serverAddr));
    if (result == SOCKET_ERROR)
    {
        std::cerr << "Send failed with error: " << WSAGetLastError() << std::endl;
    }
}
