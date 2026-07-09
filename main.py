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

    # Определяем направление прокрутки и коэффициент масштабирования
    # event.button может быть 'up' или 'down'
    base_scale = 1.1
    if event.button == "up":
        scale_factor = 1 / base_scale  # Приближение
    elif event.button == "down":
        scale_factor = base_scale  # Удаление
    else:
        scale_factor = 1

    # Получаем текущие границы графика
    xlim = ax.get_xlim()
    ylim = ax.get_ylim()

    # Вычисляем новые границы относительно точки, где находится курсор
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

    # Устанавливаем новые границы и обновляем холст
    ax.set_xlim(new_xlim)
    ax.set_ylim(new_ylim)
    event.canvas.draw_idle()


class TrafficVisualizer:
    """
    Визуализатор динамического графа города.
    Загружает статику из файлов и плавно отображает состояние симуляции из UDP-сокета.
    """

    def __init__(self, grid_size=10):
        self.port = PORT
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind((HOST, self.port))
        # Минимальный таймаут для реализации неблокирующего чтения в цикле анимации
        self.sock.settimeout(0.002)

        self.grid_size = grid_size

        # Статические данные графа
        self.nodes = []
        self.edges = []
        self.edge_lines = None
        self.node_scatter = None

        # Динамические объекты
        self.vehicles_scatter = None
        self.traffic_scatter = None

        # Реестр для плавного перемещения машин: { vehicle_id: {curr_x, curr_y, to_x, to_y} }
        self.vehicles_registry = {}

        # Настройка окна Matplotlib
        self.fig, self.ax = plt.subplots(figsize=(8, 8))
        self.fig.canvas.mpl_connect("scroll_event", on_scroll)
        self.ax.set_aspect("equal")
        self.ax.grid(True, linestyle="--", alpha=0.3)

        # Шаг 1: Загружаем статику из файлов прямо при инициализации
        self.load_static_from_files()

        # Шаг 2: Сразу отрисовываем дорожную сеть
        self.init_plot()
        self.ax.set_title("Карта загружена. Ожидание динамических данных...")

    def load_static_from_files(self):
        """Загружает структуру графа из локальных текстовых файлов."""
        # Чтение координат перекрестков (узлов)
        try:
            with open("graph_coord.txt", "r", encoding="utf-8") as f:
                lines = f.read().splitlines()
                if lines:
                    # Пропускаем первую строчку с метаданными, парсим остальные
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

        # Чтение дорог (ребер)
        try:
            with open("graph_dist.txt", "r", encoding="utf-8") as f:
                lines = f.read().splitlines()
                if lines:
                    # Пропускаем первую строчку, парсим ребра
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
        """Первичная отрисовка статических слоев графа."""
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
            # Безопасная проверка существования обоих узлов на карте
            if u and v:
                segments.append([(u["x"], u["y"]), (v["x"], v["y"])])
                valid_edges.append(edge)

        # Оставляем только те ребра, которые смогли успешно связать
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
        """Обновление внутреннего состояния симуляции из полученного пакета."""

        vehicles = data.get("vehicles", [])
        active_ids = set()
        for v in vehicles:
            # Если у машин в JSON нет явного "id", используем индекс в массиве
            v_id = v["id"]
            active_ids.add(v_id)
            tx, ty = v["x"], v["y"]

            if v_id not in self.vehicles_registry:
                # Новая машина: мгновенно ставим в начальную координату
                self.vehicles_registry[v_id] = {
                    "curr_x": tx,
                    "curr_y": ty,
                    "to_x": tx,
                    "to_y": ty,
                }
            else:
                # Существующая машина: обновляем ей конечную цель
                self.vehicles_registry[v_id]["to_x"] = tx
                self.vehicles_registry[v_id]["to_y"] = ty

        # Мягко удаляем машины, которых больше нет в активном кадре симуляции
        self.vehicles_registry = {
            v_id: val
            for v_id, val in self.vehicles_registry.items()
            if v_id in active_ids
        }

        # Обновление загруженности дорог цветом (зеленый -> красный)
        edge_states = data.get("edge_states", [])
        if edge_states and self.edge_lines:
            colors = []
            widths = []
            # Используем zip для безопасного сопоставления, даже если размеры массивов отличаются
            for state, edge in zip(edge_states, self.edges):
                congestion = state
                r = min(1.0, congestion)
                g = 1.0 - r
                colors.append((r, g, 0.0))
                widths.append(3 + 5 * congestion)
            if colors:
                self.edge_lines.set_colors(colors)
                self.edge_lines.set_linewidths(widths)

        # # Обновление состояний светофоров
        traffic_lights = data.get("traffic_lights", [])
        if traffic_lights and self.traffic_scatter:
            light_positions = []
            light_colors = []
            # for ind, tl in enumerate(traffic_lights):
            #     light_positions.append([self.nodes[ind]["x"], self.nodes[ind]["y"]])
            #         light_colors.append("green" if tl.get("state", 0) == 1 else "red")
            if light_positions:
                self.traffic_scatter.set_offsets(light_positions)
                self.traffic_scatter.set_color(light_colors)

        # Обновление размеров узлов по PageRank
        pagerank = data.get("pagerank", [])
        if pagerank and self.node_scatter:
            pr_dict = {p["node"]: p["value"] for p in pagerank}
            sizes = [150 + 400 * pr_dict.get(node["id"], 0.1) for node in self.nodes]
            self.node_scatter.set_sizes(sizes)

        # Вывод статистики
        stats = data.get("stats", {})
        total = stats.get("total_vehicles", 0)
        avg_speed = stats.get("avg_speed", 0.0)
        time_val = data.get("time", 0)
        self.ax.set_title(
            f"Время: {time_val} | Машин на карте: {total} | Ср. Скорость: {avg_speed:.1f}"
        )

    def animate_vehicles(self):
        """Выполняет шаг плавной интерполяции движения машин."""
        if self.vehicles_scatter is None:
            return

        xs = []
        ys = []
        # Скорость сглаживания (0.15 - оптимум для красивого скольжения без рывков)
        interpolation_speed = 0.15

        for v_id, v_data in self.vehicles_registry.items():
            # Линейно приближаем текущую координату к целевой
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
        """Основной цикл прослушивания сокета с высокой частотой обновления кадра."""
        plt.ion()
        self.fig.show()
        print(
            "Визуализатор запущен. Карта построена на основе конфигурационных файлов."
        )
        print("Ожидание UDP-пакетов для обновления динамических объектов...")

        while True:
            start_frame_time = time.time()

            # Читаем абсолютно все скопившиеся пакеты из буфера, чтобы не копить пинг
            last_data = None
            while True:
                try:
                    data_bytes, _ = self.sock.recvfrom(65536)
                    last_data = json.loads(data_bytes.decode())
                except socket.timeout:
                    break  # Буфер сокета пуст, переходим к отрисовке кадра
                except Exception as e:
                    print(f"Ошибка чтения данных сокета: {e}")
                    print(data_bytes.decode())
                    break

            # Если получили свежее обновление сети, применяем
            if last_data is not None:
                self.update_with_data(last_data)

            # Плавный сдвиг машин на текущем кадре анимации
            self.animate_vehicles()

            # Перерисовываем холст Matplotlib
            try:
                self.fig.canvas.draw()
                self.fig.canvas.flush_events()
            except (KeyboardInterrupt, Exception):
                break

            # Стабилизируем цикл на уровне ~50 FPS, чтобы не грузить ядро CPU на 100%
            frame_elapsed = time.time() - start_frame_time
            sleep_time = 0.02 - frame_elapsed
            if sleep_time > 0:
                time.sleep(sleep_time)


if __name__ == "__main__":
    viz = TrafficVisualizer()
    viz.run()
