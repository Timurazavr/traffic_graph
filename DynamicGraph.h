#ifndef DYNAMIC_GRAPH_H
#define DYNAMIC_GRAPH_H

#include <vector>
#include <unordered_map>
#include <string>

struct PairHash
{
    std::size_t operator()(const std::pair<int, int> &p) const
    {
        auto a = std::hash<int>{}(p.first);
        auto b = std::hash<int>{}(p.second);
        return (a ^ (b << 1));
    }
};
struct Crossroad
{
    int number, length, capacity;
    Crossroad(int number_, int length_, int capacity_) : number(number_), length(length_), capacity(capacity_) {}
};
struct Car
{
    std::pair<int, int> road_id;
    bool moving;
    int position, end_point, last_tick;

    Car(std::pair<int, int> road_id_, int position_, int end_point_) : road_id(road_id_), position(position_), end_point(end_point_)
    {
        moving = false;
        last_tick = -1;
    }
};
struct Road
{
    int num_cars;
    double average_speed, hardness, weight;
    std::vector<int> index_car;

    Road()
    {
        num_cars = 0, average_speed = 0, hardness = 0, weight = 0;
    }
};
struct Stoplight
{
    int ind_current_a, ind_current_b;
    int ind_a, ind_b;
    int time;
};
struct Vert
{
    double cost;
    int parent, vert;

    Vert(double cost_, int parent_, int vert_) : cost(cost_), parent(parent_), vert(vert_)
    {
    }
    bool operator<(const Vert &other) const
    {
        return cost > other.cost;
    }
};
struct EdgeEntry
{
    int from, to;
};

class DynamicGraph
{
private:
    std::vector<std::pair<int, int>> graph_coord_;
    std::vector<std::vector<Crossroad>> graph_dist_;
    std::unordered_map<std::pair<int, int>, Road, PairHash> roads_;
    std::vector<Car> cars_;
    std::vector<Stoplight> stoplights_;
    int current_tick_ = 0;

    std::vector<EdgeEntry> edge_list_;

    void initGraphCoordFromFile(const std::string &filename);
    void initGraphDistFromFile(const std::string &filename);
    void initCarsFromFile(const std::string &filename);
    void initStoplight();
    int search_next_crossroad(int start, int finish);
    double heuristic(int u, int v);
    std::string returnState();
    void update_stoplights();
    void update_topcar(Crossroad &crossroad, Road &road, int &car_ind, Car &car, int &next_pos);
    void update_ordinarycar(Road &road, int &car_ind, Car &car, int &next_pos);

public:
    void add_crossroad(int number);
    void add_road(int crossroad1, int crossroad2, int length, int capacity);
    void add_car(int start, int finish);
    const Crossroad &find_crossroad(int v, int u);
    std::string tick();

    DynamicGraph(const std::string &filename_coord, const std::string &filename_dist, const std::string &filename_cars);
    ~DynamicGraph() {}
};

#endif