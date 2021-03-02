import open3d as o3d
import matplotlib.pyplot as plt
import numpy as np
from surfacedetector.utility.line_mesh import LineMesh
from scripts.o3d_util import create_grid, create_box, tranform_vectors, rotate_vectors, create_transform, create_point


np.set_printoptions(precision=3, suppress=True)

# Flip Y to Z, Z to -Y
MOUNT_TO_SENSOR_ROT = np.linalg.inv(np.array([
    [1, 0, 0],
    [0, 0, -1],
    [0, 1, 0]
]))

def compute_2D_angle_difference(vector1, vector2):
    angle = np.arctan2(vector2[1], vector2[0]) - np.arctan2(vector1[1], vector1[0])
    return np.degrees(angle)

def compute_turning_angles(platform_poi_pos_wheel_chair_frame, platform_normal_wheel_chair_frame, debug=False):
    wheel_chair_pos_in_wheel_chair_frame = np.array([0.0,0.0,0.0]) # The position will be 0 in wheel chair frame (origin)
    wheel_chair_dir_vec_unit = np.array([0.0, 1.0, 0.0]) # forward y-axis is wheel chair direction

    vec_wheelchair_to_poi = platform_poi_pos_wheel_chair_frame - wheel_chair_pos_in_wheel_chair_frame # called Vec3 (blue) in diagrams
    vec_wheel_chair_to_poi_2D = vec_wheelchair_to_poi[:2] # the z-axis is height in this reference frame
    dist = np.linalg.norm(vec_wheel_chair_to_poi_2D)
    vec_wheel_chair_to_poi_2D_unit = vec_wheel_chair_to_poi_2D / dist

    platform_normal_inverted_unit = -platform_normal_wheel_chair_frame # called Vec2 (red) in diagrams

    alpha = compute_2D_angle_difference(wheel_chair_dir_vec_unit, vec_wheel_chair_to_poi_2D_unit)
    beta = compute_2D_angle_difference(wheel_chair_dir_vec_unit,platform_normal_inverted_unit )


    first_turn = alpha
    second_turn = -alpha + beta
    if debug:
        print(f"Alpha Angle {alpha:.1f}; Beta Angle: {beta:.1f}")
        print(f"First Turn CC: {first_turn:.1f} degres; Move Distance: {dist:.2f};  Second Turn: {second_turn:.1f}")

    return dict(alpha=alpha, beta=beta, dist=dist, first_turn=first_turn, second_turn=second_turn, 
                vec_wheel_chair_to_poi_2D_unit=vec_wheel_chair_to_poi_2D_unit, platform_normal_inverted_unit=platform_normal_inverted_unit)


def main():
    # Contants you can change
    POI_OFFSET = 0.5
    PLATFORM_WIDTH = 1.5
    PLATFORM_HEIGHT = 0.25
    WHEEL_CHAIR_POS = np.array([1.0, -1.0, 0])
    WHEEL_CHAIR_ROT = dict(roll=0, pitch=0, yaw=10)
    SENSOR_MOUNT_POS = np.array([0.25, 0.25, 0.7])
    SENSOR_MOUNT_ROT = dict(roll=0, pitch=-15, yaw=0)
    SENSOR_POS = np.array([0, 0.025, 0.025])

    # Creates origin coordinate frame and grid
    global_frame = o3d.geometry.TriangleMesh.create_coordinate_frame(size=0.2)
    grid = create_grid(size=5, n=20) # each square is 25X25 CM, size is 5X5

    # Defnitions of the Platform Box, Platform Center Point, and Platform Point of Interest (POI) 
    platform = dict(parent=None, center_point=np.array([0, 2, 0]), depth=PLATFORM_HEIGHT, width=PLATFORM_WIDTH, height=1.0, rotation=dict(roll=0, pitch=0, yaw=0))
    platform_cp = dict(parent=platform, center_point=np.array([0, -0.5, 0.125]), size=0.02, rotation=dict(roll=0, pitch=0, yaw=0), color=[1,0,0])
    platform_poi = dict(parent=platform, center_point=np.array([0, -0.5 - POI_OFFSET, 0.125]), size=0.02, rotation=dict(roll=0, pitch=0, yaw=0), color=[0,1,0])

    # Wheel Chair Box, Sensor Mount, and Sensor
    wheel_chair = dict(parent=None, center_point=WHEEL_CHAIR_POS, depth=0.7, width=0.5, height=0.5, rotation=WHEEL_CHAIR_ROT)
                                            # offset from wheel chair center          rotation from wheel chair frame
    sensor_mount = dict(parent=wheel_chair, center_point=SENSOR_MOUNT_POS, rotation=SENSOR_MOUNT_ROT, width=0.1, depth=0.05, height=0.03)
    sensor = dict(parent=sensor_mount, center_point=SENSOR_POS, rotation=dict(roll=0, pitch=0, yaw=0), post_rot=MOUNT_TO_SENSOR_ROT, width=0.01, depth=0.025, height=0.01)

    # Create Open 3D Geometries, these geometries are defined in the WORLD FRAME, these geometries can then be visualized below
    # You don't need to understand these functions, they just returns a geometry to render
    platform_geom = create_box(platform)
    platform_cp_geom = create_point(platform_cp)
    platform_poi_geom = create_point(platform_poi)
    wheel_chair_geom = create_box(wheel_chair)
    sensor_mount_geom = create_box(sensor_mount)
    sensor_geom = create_box(sensor)

    # Get sensor, poi, and wheelchair 3D position and 2D projections in WORLD frame
    sensor_pos_world = sensor['geom'].get_center()
    platform_cp_pos_world = platform_cp['geom'].get_center()
    platform_poi_pos_world = platform_poi['geom'].get_center()
    wheel_chair_pos_world = wheel_chair['geom'].get_center()
    sensor_pos_world_proj = np.copy(sensor_pos_world)
    platform_poi_pos_world_proj = np.copy(platform_poi_pos_world)
    wheel_chair_pos_world_proj = np.copy(wheel_chair_pos_world)
    sensor_pos_world_proj[2] = 0
    platform_poi_pos_world_proj[2] = 0
    wheel_chair_pos_world_proj[2] = 0

    # Create lines between wheel chair center and poi (Blue) and INCORRECT LINE between sensor frame and poi (RED)
    vec3_geom_1 = LineMesh([sensor_pos_world, platform_poi_pos_world, sensor_pos_world_proj, platform_poi_pos_world_proj ], lines=[[0, 1], [2,3]], radius=0.005, colors=[1, 0, 0])
    vec3_geom_2 = LineMesh([wheel_chair_pos_world_proj, platform_poi_pos_world_proj], lines=[[0, 1]], radius=0.005, colors=[0, 0, 1])

    # Simulate POI and wall_normal in SENSOR frame, this is what is generated by RealSense Frame
    transform = np.linalg.inv(sensor['transform'])
    platform_cp_pos_sensor = tranform_vectors(platform_cp_pos_world, transform )
    platform_normal_sensor = rotate_vectors([0, -1, 0], transform )
    platform_poi_pos_sensor = tranform_vectors(platform_poi_pos_world, transform )


    # Transform POI3D and Wall Normal into WHEELCHAIR frame, all you need are the constants SENSOR_MOUNT_POS, SENSOR_MOUNT_ROT, SENSOR_POS, MOUNT_TO_SENSOR_ROT
    SENSOR_TO_WHEEL_CHAIR = create_transform(SENSOR_MOUNT_POS, SENSOR_MOUNT_ROT) @ create_transform(SENSOR_POS, MOUNT_TO_SENSOR_ROT)
    platform_cp_pos_wheel_chair = tranform_vectors(platform_cp_pos_sensor, SENSOR_TO_WHEEL_CHAIR)
    platform_normal_wheel_chair = rotate_vectors(platform_normal_sensor, SENSOR_TO_WHEEL_CHAIR)
    # platform_poi_pos_wheel_chair = tranform_vectors(platform_poi_pos_sensor, SENSOR_TO_WHEEL_CHAIR)
    platform_poi_pos_wheel_chair = platform_normal_wheel_chair * POI_OFFSET + platform_cp_pos_wheel_chair # this line will result in the same calculation as above, VERIFIED

    print(f"Platform POI in World Frame: {platform_poi_pos_world}")
    print(f"Platform POI in Sensor Frame: {platform_poi_pos_sensor}")
    print(f"Platform POI in Wheel Chair Frame: {platform_poi_pos_wheel_chair}")
    print(f"Platform Normal in Wheel Chair Frame: {platform_normal_wheel_chair}")


    print("\nCalculated Angles....Creating Turn Procedure")
    result = compute_turning_angles(platform_poi_pos_wheel_chair, platform_normal_wheel_chair, debug=True)

    fig, ax = plt.subplots(1, 1)
    ax.scatter(platform_poi_pos_wheel_chair[0] + 0.03, platform_poi_pos_wheel_chair[1], c=[[0, 1, 0]])
    ax.text(platform_poi_pos_wheel_chair[0], platform_poi_pos_wheel_chair[1], 'poi')
    ax.scatter(0, 0, c='k')
    ax.text(0.01, 0, 'Wheel Chair')
    ax.arrow(0.0, 0.0, 0, 1, ec='g', fc='g', width=.01)
    ax.arrow(0.0, 0.0, result['vec_wheel_chair_to_poi_2D_unit'][0], result['vec_wheel_chair_to_poi_2D_unit'][1], ec='b', fc='b', width=.01)
    ax.arrow(0.0, 0.0, result['platform_normal_inverted_unit'][0], result['platform_normal_inverted_unit'][1], ec='r', fc='r', width=.01)
    ax.text(result['vec_wheel_chair_to_poi_2D_unit'][0], (result['vec_wheel_chair_to_poi_2D_unit'][1] + 1) / 2.0, rf'$\alpha={result["alpha"]:.0f}^\circ$')
    ax.text((result['vec_wheel_chair_to_poi_2D_unit'][0] + result['platform_normal_inverted_unit'][0]) / 2.0, 
        (result['vec_wheel_chair_to_poi_2D_unit'][1] + result['platform_normal_inverted_unit'][1]) / 2.0, rf'$\beta={result["beta"]:.0f}^\circ$')
    ax.axis('equal')
    plt.draw()
    plt.pause(0.01)

    o3d.visualization.draw_geometries([global_frame, grid, *wheel_chair_geom, *platform_geom, *platform_cp_geom, 
                                        *platform_poi_geom,*sensor_mount_geom, sensor_geom[1],
                                        *vec3_geom_1.cylinder_segments, *vec3_geom_2.cylinder_segments])



if __name__ == "__main__":
    main()



