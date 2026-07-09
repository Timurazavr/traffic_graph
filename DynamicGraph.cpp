#include <iostream>
#include <fstream>
#include <vector>
#include <unordered_map>
#include <queue>
#include <string>
#include <limits>
#include <cmath>
#include "DynamicGraph.h"

const int INF = std::numeric_limits<int>::max();
const int PERIOD_STOPLIGHT = 20;
const double TICK = 0.2;
const int SPEED = 5; // 90kmh = 25ms

DynamicGraph::DynamicGraph(const std::string &filename_coord, const std::string &filename_dist, const std::string &filename_cars)
{
    initGraphCoordFromFile(filename_coord);
    initGraphDistFromFile(filename_dist);
    initCarsFromFile(filename_cars);
    initStoplight();
}

void DynamicGraph::add_road(int crossroad1, int crossroad2, int length, int capacity)
{
    edge_list_.push_back({crossroad1, crossroad2});
    graph_dist_[crossroad1].push_back(Crossroad(crossroad2, length, capacity));
    roads_[{crossroad1, crossroad2}] = Road();
}
void DynamicGraph::add_car(int start, int finish)
{
    int next_node = search_next_crossroad(start, finish);
    if (next_node == -1)
        return;
    cars_.push_back(Car({start, next_node}, 0, finish));
    roads_[{start, next_node}].index_car.push_back(cars_.size() - 1);
}
void DynamicGraph::initGraphCoordFromFile(const std::string &filename)
{
    std::ifstream file(filename);
    if (!file.is_open())
    {
        std::cout << "Failed to open graph coord file!\n";
        return;
    }
    int v;
    if (!(file >> v))
        return;
    graph_coord_.resize(v);
    for (int i = 0; i < v; i++)
    {
        int number, x, y;
        if (file >> number >> x >> y)
        {
            graph_coord_[number] = {x, y};
        }
    }
    file.close();
}
void DynamicGraph::initGraphDistFromFile(const std::string &filename)
{
    std::ifstream file(filename);
    if (!file.is_open())
    {
        std::cout << "Failed to open graph dist file!\n";
        return;
    }
    int v, e;
    if (!(file >> v >> e))
        return;
    graph_dist_.resize(v);
    for (int i = 0; i < e; i++)
    {
        int crossroad1, crossroad2, length, capacity;
        if (file >> crossroad1 >> crossroad2 >> length >> capacity)
        {
            add_road(crossroad1, crossroad2, length, capacity);
        }
    }
    file.close();
}
void DynamicGraph::initCarsFromFile(const std::string &filename)
{
    std::ifstream file(filename);
    if (!file.is_open())
    {
        std::cout << "Failed to open cars file!\n";
        return;
    }
    int n;
    if (!(file >> n))
        return;
    for (int i = 0; i < n; i++)
    {
        int start, finish;
        if (file >> start >> finish)
        {
            add_car(start, finish);
        }
    }
    file.close();
}
void DynamicGraph::initStoplight()
{
    stoplights_.resize(graph_coord_.size());
    for (int i = 0; i < stoplights_.size(); i++)
    {
        stoplights_[i].ind_a = 0;
        stoplights_[i].ind_b = 1;
        stoplights_[i].ind_current_a = graph_dist_[i][stoplights_[i].ind_a].number;
        stoplights_[i].ind_current_b = graph_dist_[i][stoplights_[i].ind_b].number;
        stoplights_[i].time = PERIOD_STOPLIGHT;
    }
}
double DynamicGraph::heuristic(int u, int v)
{
    int dx = graph_coord_[u].first - graph_coord_[v].first;
    int dy = graph_coord_[u].second - graph_coord_[v].second;
    return (std::sqrt(double(dx * dx + dy * dy)));
};
int DynamicGraph::search_next_crossroad(int start, int finish)
{
    if (start == finish)
        return start;

    std::vector<double> cost(graph_dist_.size(), INF);
    std::vector<int> parent(graph_dist_.size(), -1);
    std::priority_queue<Vert> queue;

    cost[start] = 0;
    double start_f = heuristic(start, finish);
    queue.push(Vert(start_f, start, start));

    while (!queue.empty())
    {
        Vert current = queue.top();
        queue.pop();

        double current_g = current.cost - heuristic(current.vert, finish);

        if (current_g > cost[current.vert])
            continue;

        if (current.vert == finish)
            break;

        for (const auto &crossroad : graph_dist_[current.vert])
        {
            double next_g = current_g + crossroad.length;

            if (next_g < cost[crossroad.number])
            {
                cost[crossroad.number] = next_g;
                parent[crossroad.number] = current.vert;

                double next_f = next_g + heuristic(crossroad.number, finish);
                queue.push(Vert(next_f, current.vert, crossroad.number));
            }
        }
    }

    if (parent[finish] == -1)
        return -1;

    int cur = finish;
    while (parent[cur] != start && parent[cur] != -1)
        cur = parent[cur];
    return cur;
}
void DynamicGraph::update_stoplights()
{
    for (int i = 0; i < stoplights_.size(); i++)
    {
        Stoplight &stoplight = stoplights_[i];
        if (stoplight.time > TICK)
        {
            stoplight.time -= TICK;
        }
        else
        {
            stoplight.time = PERIOD_STOPLIGHT;
            stoplight.ind_b = (stoplight.ind_b + 1) % graph_dist_[i].size();
            stoplight.ind_a = (stoplight.ind_a + 1) % graph_dist_[i].size();
            stoplight.ind_current_a = graph_dist_[i][stoplight.ind_a].number;
            stoplight.ind_current_b = graph_dist_[i][stoplight.ind_b].number;
        }
    }
}
void DynamicGraph::update_topcar(Crossroad &crossroad, Road &road, int &car_ind, Car &car, int &next_pos)
{
    if (next_pos < crossroad.length)
    {
        car.position = next_pos;
        car_ind++;
        return;
    }

    // Проверка прибытия в конечную точку маршрута
    if (car.end_point == crossroad.number)
    {
        cars_[road.index_car[car_ind]].end_point = -1;
        road.index_car.erase(road.index_car.begin() + car_ind);
        // Индекс не увелич, элемент удален
        return;
    }

    // Проверка зеленого света светофора
    if (stoplights_[crossroad.number].ind_current_a != car.road_id.first && stoplights_[crossroad.number].ind_current_b != car.road_id.first)
    { // Если горит красный стоим
        car.position = crossroad.length;
        car_ind++;
        return;
    }

    // Поиск следующего отрезка пути
    int next_crossroad = search_next_crossroad(crossroad.number, car.end_point);
    if (next_crossroad == -1)
    {
        car.position = crossroad.length;
        car_ind++;
        return;
    }

    std::pair<int, int> next_road_id = {crossroad.number, next_crossroad};
    Road &next_road = roads_[next_road_id];

    // Проверяем есть ли место на следующей дороге
    if (!next_road.index_car.empty() and cars_[next_road.index_car.back()].position == 0)
    {
        car.position = crossroad.length;
        car_ind++;
        return;
    }

    // Если место есть перемещаем на новую дорогу
    car.road_id = next_road_id;
    next_road.index_car.push_back(road.index_car[car_ind]);
    road.index_car.erase(road.index_car.begin() + car_ind);

    if (next_road.index_car.size() == 1)
    {
        car.position = std::min(next_pos - crossroad.length, find_crossroad(crossroad.number, next_crossroad).length);
    }
    else
    {
        Car &prev_car = cars_[next_road.index_car[next_road.index_car.size() - 2]];
        car.position = std::min(next_pos - crossroad.length, prev_car.position - 1);
    }
    // Индекс не увелич, элемент удален
}
void DynamicGraph::update_ordinarycar(Road &road, int &car_ind, Car &car, int &next_pos)
{
    Car &prev_car = cars_[road.index_car[car_ind - 1]];

    car.position = std::min(next_pos, prev_car.position - 1);
    car_ind++;
}
std::string DynamicGraph::tick()
{
    current_tick_++;

    update_stoplights();

    for (int start_node = 0; start_node < graph_dist_.size(); ++start_node)
    {
        for (auto &crossroad : graph_dist_[start_node])
        {
            Road &road = roads_[{start_node, crossroad.number}];

            int car_ind = 0;
            while (car_ind < road.index_car.size())
            {
                Car &car = cars_[road.index_car[car_ind]];

                if (car.last_tick == current_tick_)
                {
                    car_ind++;
                    continue;
                }
                car.last_tick = current_tick_;

                int next_pos = car.position + SPEED * TICK;
                if (car_ind == 0)
                {
                    update_topcar(crossroad, road, car_ind, car, next_pos);
                }
                else
                {
                    update_ordinarycar(road, car_ind, car, next_pos);
                }
            }
        }
    }
    return (returnState());
}
const Crossroad &DynamicGraph::find_crossroad(int v, int u)
{
    for (const Crossroad &crossroad : graph_dist_[v])
    {
        if (crossroad.number == u)
            return crossroad;
    }
    throw std::runtime_error("Crossroad not found");
    exit(1);
}
std::string DynamicGraph::returnState()
{
    std::string json = "{";
    json += "\"time\":" + std::to_string(current_tick_) + ",";

    json += "\"vehicles\":[";
    int active_cars = 0;
    double total_speed = 0;
    for (int i = 0; i < cars_.size(); i++)
    {
        const Car &car = cars_[i];
        if (car.end_point == -1)
            continue;
        active_cars++;

        double car_speed = 0.0;

        total_speed += car_speed;

        int u = car.road_id.first;
        int v = car.road_id.second;

        const Crossroad &crossroad = find_crossroad(u, v);

        double dist = (double)car.position / crossroad.length;
        double x = graph_coord_[u].first + dist * (graph_coord_[v].first - graph_coord_[u].first);
        double y = graph_coord_[u].second + dist * (graph_coord_[v].second - graph_coord_[u].second);

        json += "{\"id\":" + std::to_string(i) + ",\"x\":" + std::to_string(x) + ",\"y\":" + std::to_string(y) + "},";
    }
    if (active_cars > 0)
        json.pop_back();
    json += "],";

    json += "\"edge_states\":[";
    for (size_t i = 0; i < edge_list_.size(); i++)
    {
        int u = edge_list_[i].from;
        int v = edge_list_[i].to;
        int cap = find_crossroad(u, v).capacity;

        const Road &road = roads_[{u, v}];

        double congestion = (double)road.index_car.size() / cap;

        json += std::to_string(std::min(1.0, congestion)) + ",";
    }
    if (!edge_list_.empty())
        json.pop_back();
    json += "],";

    json += "\"traffic_lights\":[";
    for (size_t i = 0; i < stoplights_.size(); i++)
    {
        json += "[" + std::to_string(stoplights_[i].ind_current_a) + ",";
        json += std::to_string(stoplights_[i].ind_current_b) + "],";
    }
    if (!stoplights_.empty())
        json.pop_back();
    json += "],";

    json += "\"pagerank\":[";
    for (size_t i = 0; i < graph_dist_.size(); i++)
    {
        double pr = (double)graph_dist_[i].size() / (edge_list_.size() ? edge_list_.size() : 1);
        json += "{\"node\":" + std::to_string(i) + ",\"value\":" + std::to_string(pr) + "}";
        if (i + 1 < graph_dist_.size())
            json += ",";
    }
    json += "],";

    double avg = active_cars > 0 ? total_speed / active_cars : 0.0;
    json += "\"stats\":{";
    json += "\"total_vehicles\":" + std::to_string(active_cars) + ",";
    json += "\"avg_speed\":" + std::to_string(avg);
    json += "}}";
    return json;
}