#include "Socket.h"
#include "DynamicGraph.h"
#include <iostream>
#include <thread>
#include <chrono>
#include <string>

const int PORT = 12345;
const char *IP = "127.0.0.1";

int main()
{
    Socket socket(PORT, IP);

    DynamicGraph graph("graph_coord.txt", "graph_dist.txt", "cars.txt");
    // graph.add_car(0, 3);

    std::cout << "Simulated started!" << std::endl;
    while (true)
    {
        std::string json_str = graph.tick();
        // std::cout << json_str << std::endl;
        socket.send(json_str);
        std::this_thread::sleep_for(std::chrono::milliseconds(100));
    }
    return 0;
}