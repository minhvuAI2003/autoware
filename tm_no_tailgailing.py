import carla
import math
import time

client = carla.Client("127.0.0.1", 2000)
client.set_timeout(10.0)

world = client.get_world()


def is_directly_behind_ego(ego, veh, max_dist=30.0, max_angle_deg=10.0):
    ego_tf = ego.get_transform()
    ego_loc = ego_tf.location
    veh_loc = veh.get_location()

    yaw = math.radians(ego_tf.rotation.yaw)

    # Vector hướng trước của ego
    forward_x = math.cos(yaw)
    forward_y = math.sin(yaw)

    # Vector hướng sau của ego
    backward_x = -forward_x
    backward_y = -forward_y

    # Vector từ ego tới vehicle
    dx = veh_loc.x - ego_loc.x
    dy = veh_loc.y - ego_loc.y

    dist = math.sqrt(dx * dx + dy * dy)

    if dist < 1e-6:
        return False

    if dist > max_dist:
        return False

    # Chuẩn hóa vector ego -> vehicle
    dir_x = dx / dist
    dir_y = dy / dist

    # Cos góc giữa vector ego->vehicle và hướng sau của ego
    cos_angle = dir_x * backward_x + dir_y * backward_y

    # Tránh lỗi số học
    cos_angle = max(-1.0, min(1.0, cos_angle))

    angle_deg = math.degrees(math.acos(cos_angle))

    # angle_deg gần 0 nghĩa là xe nằm ngay phía sau chính diện
    return angle_deg <= max_angle_deg


while True:
    vehicles = world.get_actors().filter("vehicle.*")

    ego = None
    for v in vehicles:
        if v.attributes.get("role_name") in ["ego_vehicle", "hero"]:
            ego = v
            break

    if ego is None:
        print("Không tìm thấy ego vehicle")
        time.sleep(1)
        continue

    for v in vehicles:
        if v.id == ego.id:
            continue

        if is_directly_behind_ego(
            ego,
            v,
            max_dist=10.0,
            max_angle_deg=10.0
        ):
            print(f"Destroy directly rear NPC vehicle {v.id}")
            v.destroy()

    time.sleep(0.5)