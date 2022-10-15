import cv2
import math
import functions as f
from datetime import datetime

messages = []


def send_message(message, m):
    """

    :param message:
    :param m:
    :return:
    """
    m.append(message)


def print_messages(image, m, y=700):
    """

    :param image:
    :param m:
    :param y:
    :return:
    """
    i = 0

    for message in m:
        cv2.putText(image, message, (50, y - i * 30), cv2.FONT_HERSHEY_SIMPLEX, 0.75, (255, 255, 0), 2)
        i += 1

    m.clear()


def get_angle_between_two_points(point1, point2):
    angle = 360 - math.atan2(point2[1] - point1[1], point2[0] - point1[0]) * 180 / math.pi

    return angle


def read(img, me=None, m=None, size=None):
    """

    :param img:
    :param me:
    :param m:
    :param size:
    :return:
    """
    # Datetime
    now = datetime.now()
    send_message(now.strftime("%d/%m/%Y, %H:%M:%S"), messages)

    # Pixels per meter
    ppm = 420
    # Area to scan
    area_height = 1.20
    area_width = 1.40
    area_ratio = area_height / area_width
    # In cm
    center_width = 0.10

    # Resizing image
    if size is not None:
        img_resize = cv2.resize(img, size)
    else:
        img_resize = img

    # Middle point of image
    middle = img_resize.shape[1] // 2
    # Width of image
    w = img_resize.shape[1]
    # Height of image
    h = img_resize.shape[0]
    # Left side of image
    img_left = img_resize[0:h, 0:middle]
    # Right side of image
    img_right = img_resize[0:h, middle:w]

    c_x = int(w // 2)
    c_y = int(h // 2)

    # Aruco dictionary 4x4_50
    aruco_dict = cv2.aruco.Dictionary_get(cv2.aruco.DICT_4X4_50)
    # Aruco params
    aruco_params = cv2.aruco.DetectorParameters_create()
    # Reading aruco markers detected on the left side
    l_markers = f.draw_markers(img_left, img_resize, aruco_dict, aruco_params, 0)
    # Reading aruco markers detected on the right side
    r_markers = f.draw_markers(img_right, img_resize, aruco_dict, aruco_params, middle)

    if me is not None:
        send_message("Battery Level: " + str(me.get_battery()) + "%", messages)

    movements = [0, 0, 0, 0]

    # Distance
    if len(l_markers) == 1 and len(r_markers) == 1:
        p1 = l_markers[0][0]
        p2 = r_markers[0][0]
        a1 = l_markers[0][2]
        a2 = r_markers[0][2]
        # Area Difference
        if a1 > 0 and a2 > 0:
            delta_area = (1 - a2/a1) * 100
        # print(p1, " - ", p2)
        angle = get_angle_between_two_points(p1, p2)
        f.put_text(img_resize, "Angle: " + str(round(angle, 2)) + " degrees", 600, 140)
        f.put_text(img_resize, "Delta Area: " + str(round(delta_area, 2)) + "%", 600, 170)
        distance = f.distance_in_meters(math.dist(p1, p2), ppm)
        # Delta yaw
        delta_d = int((distance - area_width) * 100)
        f.put_text(img_resize, "Delta D: " + str(delta_d) + " cms", 600, 110)
        # ppm from image
        ppmi = distance / area_width * ppm
        width_center = f.distance_in_pixels(center_width, ppmi)
        send_message("Distance: " + str(round(distance, 2)) + " m", messages)
        # Height of area with reference of width in picture
        distance = distance * area_ratio
        distance = f.distance_in_pixels(distance, ppm)
        delta_x, delta_y = f.draw_rectangle(img_resize, p1, p2, distance, (c_x, c_y), width_center)
        delta_x, delta_y = int(f.distance_in_meters(delta_x, ppmi / 100)), int(
            f.distance_in_meters(delta_y, ppmi / 100))
        f.put_text(img_resize, "Delta X: " + str(int(delta_x)) + " cms", 600, 50)
        f.put_text(img_resize, "Delta Y: " + str(int(delta_y)) + " cms", 600, 80)
        # def movements(delta, delta_width, width_center, image):
        movements = f.movements((delta_x, delta_y), delta_d, center_width * 100, img_resize)
        # movements = [delta_x, delta_y, delta_d]
        send_message("Roll - Throttle - Pitch - Yaw: " + str(movements), messages)

    if m is None:
        m = []
    for message in m:
        send_message(message, messages)

    print_messages(img_resize, messages)
    cv2.imshow("Output", img_resize)

    # cv2.imshow("Left", img_left)
    # cv2.imshow("Right", img_right)

    return movements, img_resize