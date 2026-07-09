import json
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection
import socket
import time

HOST = "127.0.0.1"
PORT = 12345


def on_scroll(event):
    ax = event.inaxes
    if ax is None:
        return

    base_scale = 1.1
    if event.button == "up":
        scale_factor = 1 / base_scale
    elif event.button == "down":
        scale_factor = base_scale
    else:
        scale_factor = 1

    xlim = ax.get_xlim()
    ylim = ax.get_ylim()

    xdata = event.xdata
    ydata = event.ydata

    new_xlim = [
        xdata - (xdata - xlim[0]) * scale_factor,
        xdata + (xlim[1] - xdata) * scale_factor,
    ]
    new_ylim = [
        ydata - (ydata - ylim[0]) * scale_factor,
        ydata + (ylim[1] - ydata) * scale_factor,
    ]

    ax.set_xlim(new_xlim)
    ax.set_ylim(new_ylim)
    event.canvas.draw_idle()


class TrafficVisualizer:
    def __init__(self, grid_size=10):
        self.port = PORT
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind((HOST, self.port))

        self.sock.settimeout(0.002)

        self.grid_size = grid_size

        self.nodes = []
        self.edges = []
        self.edge_lines = None
        self.node_scatter = None

        self.vehicles_scatter = None
        self.traffic_scatter = None

        self.vehicles_registry = {}

        self.fig, self.ax = plt.subplots(figsize=(8, 8))
        self.fig.canvas.mpl_connect("scroll_event", on_scroll)
        self.ax.set_aspect("equal")
        self.ax.grid(True, linestyle="--", alpha=0.3)

        self.load_static_from_files()

        self.init_plot()
        self.ax.set_title("Карта загружена. Ожидание динамических данных")

    def load_static_from_files(self):
        try:
            with open("graph_coord.txt", "r", encoding="utf-8") as f:
                lines = f.read().splitlines()
                if lines:
                    for line in lines[1:]:
                        line = line.strip()
                        if not line:
                            continue
                        parts = line.split()
                        if len(parts) >= 3:
                            self.nodes.append(
                                {
                                    "id": int(parts[0]),
                                    "x": float(parts[1]),
                                    "y": float(parts[2]),
                                }
                            )
            print(f"Успешно загружено узлов: {len(self.nodes)}")
        except Exception as e:
            print(f"Ошибка при чтении graph_coordinates.txt: {e}")

        try:
            with open("graph_dist.txt", "r", encoding="utf-8") as f:
                lines = f.read().splitlines()
                if lines:
                    for line in lines[1:]:
                        line = line.strip()
                        if not line:
                            continue
                        parts = line.split()
                        if len(parts) >= 2:
                            self.edges.append(
                                {"from": int(parts[0]), "to": int(parts[1])}
                            )
            print(f"Успешно загружено дорог: {len(self.edges)}")
        except Exception as e:
            print(f"Ошибка при чтении graph_dist.txt: {e}")

    def init_plot(self):
        if not self.nodes:
            return

        xs = [n["x"] for n in self.nodes]
        ys = [n["y"] for n in self.nodes]

        self.node_scatter = self.ax.scatter(
            xs,
            ys,
            s=250,
            c="lightblue",
            edgecolors="black",
            zorder=2,
            label="Перекрёстки",
        )

        segments = []
        valid_edges = []
        for edge in self.edges:
            u = next((n for n in self.nodes if n["id"] == edge["from"]), None)
            v = next((n for n in self.nodes if n["id"] == edge["to"]), None)

            if u and v:
                segments.append([(u["x"], u["y"]), (v["x"], v["y"])])
                valid_edges.append(edge)

        self.edges = valid_edges

        self.edge_lines = LineCollection(
            segments, colors="gray", linewidths=3, zorder=1, label="Дороги"
        )
        self.ax.add_collection(self.edge_lines)

        self.vehicles_scatter = self.ax.scatter(
            [], [], s=50, c="purple", marker="o", zorder=4, label="Машины"
        )
        self.traffic_scatter = self.ax.scatter(
            [], [], s=120, marker="s", edgecolors="black", zorder=3, label="Светофоры"
        )

        max_x = max(xs) + 1.5
        max_y = max(ys) + 1.5
        min_x = min(xs) - 1.5
        min_y = min(ys) - 1.5
        self.ax.set_xlim(min_x, max_x)
        self.ax.set_ylim(min_y, max_y)

        self.ax.legend(loc="upper right")

    def update_with_data(self, data):

        vehicles = data.get("vehicles", [])
        active_ids = set()
        for v in vehicles:
            v_id = v["id"]
            active_ids.add(v_id)
            tx, ty = v["x"], v["y"]

            if v_id not in self.vehicles_registry:
                self.vehicles_registry[v_id] = {
                    "curr_x": tx,
                    "curr_y": ty,
                    "to_x": tx,
                    "to_y": ty,
                }
            else:
                self.vehicles_registry[v_id]["to_x"] = tx
                self.vehicles_registry[v_id]["to_y"] = ty

        self.vehicles_registry = {
            v_id: val
            for v_id, val in self.vehicles_registry.items()
            if v_id in active_ids
        }

        edge_states = data.get("edge_states", [])
        if edge_states and self.edge_lines:
            colors = []
            widths = []

            for state, edge in zip(edge_states, self.edges):
                congestion = state
                r = min(1.0, congestion)
                g = 1.0 - r
                colors.append((r, g, 0.0))
                widths.append(3 + 5 * congestion)
            if colors:
                self.edge_lines.set_colors(colors)
                self.edge_lines.set_linewidths(widths)

        traffic_lights = data.get("traffic_lights", [])
        if traffic_lights and self.traffic_scatter:
            green_map = {}
            for idx, entry in enumerate(traffic_lights):
                if isinstance(entry, dict):
                    node_id = entry.get("node", entry.get("id"))
                    green_from = entry.get("tl", [])
                else:
                    node_id = self.nodes[idx]["id"] if idx < len(self.nodes) else None
                    green_from = entry
                if node_id is not None:
                    green_map[node_id] = set(green_from)

            node_by_id = {n["id"]: n for n in self.nodes}

            offset_ratio = 0.1

            light_positions = []
            light_colors = []
            for edge in self.edges:
                from_id, to_id = edge["from"], edge["to"]

                if to_id not in green_map:
                    continue

                u = node_by_id.get(from_id)
                v = node_by_id.get(to_id)
                if not u or not v:
                    continue

                lx = v["x"] + (u["x"] - v["x"]) * offset_ratio
                ly = v["y"] + (u["y"] - v["y"]) * offset_ratio
                light_positions.append((lx, ly))

                is_green = from_id in green_map[to_id]
                light_colors.append("#2ecc71" if is_green else "#e74c3c")

            if light_positions:
                self.traffic_scatter.set_offsets(light_positions)
                self.traffic_scatter.set_color(light_colors)
            else:
                self.traffic_scatter.set_offsets(np.empty((0, 2)))

        pagerank = data.get("pagerank", [])
        if pagerank and self.node_scatter:
            pr_dict = {p["node"]: p["value"] for p in pagerank}
            sizes = [150 + 400 * pr_dict.get(node["id"], 0.1) for node in self.nodes]
            self.node_scatter.set_sizes(sizes)

        stats = data.get("stats", {})
        total = stats.get("total_vehicles", 0)
        avg_speed = stats.get("avg_speed", 0.0)
        time_val = data.get("time", 0)
        self.ax.set_title(
            f"Время: {time_val} | Машин на карте: {total} | Ср. Скорость: {avg_speed:.1f}"
        )

    def animate_vehicles(self):
        if self.vehicles_scatter is None:
            return

        xs = []
        ys = []

        interpolation_speed = 0.15

        for v_id, v_data in self.vehicles_registry.items():
            v_data["curr_x"] += (
                v_data["to_x"] - v_data["curr_x"]
            ) * interpolation_speed
            v_data["curr_y"] += (
                v_data["to_y"] - v_data["curr_y"]
            ) * interpolation_speed
            xs.append(v_data["curr_x"])
            ys.append(v_data["curr_y"])

        if xs:
            self.vehicles_scatter.set_offsets(np.c_[xs, ys])
        else:
            self.vehicles_scatter.set_offsets(np.empty((0, 2)))

    def run(self):
        plt.ion()
        self.fig.show()
        print("Визуализатор запущен")
        print("Ожидание UDP пакетов")

        while True:
            start_frame_time = time.time()

            last_data = None
            while True:
                try:
                    data_bytes, _ = self.sock.recvfrom(65536)
                    last_data = json.loads(data_bytes.decode())
                except socket.timeout:
                    break
                except Exception as e:
                    print(f"Ошибка чтения данных сокета: {e}")
                    print(data_bytes.decode())
                    break

            if last_data is not None:
                self.update_with_data(last_data)

            self.animate_vehicles()

            try:
                self.fig.canvas.draw()
                self.fig.canvas.flush_events()
            except (KeyboardInterrupt, Exception):
                break

            frame_elapsed = time.time() - start_frame_time
            sleep_time = 0.02 - frame_elapsed
            if sleep_time > 0:
                time.sleep(sleep_time)


if __name__ == "__main__":
    viz = TrafficVisualizer()
    viz.run()
