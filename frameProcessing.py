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


def read(img, me=None, m=None, size=None, print_text=True, range_ids=None, output=False, offset_height=1.4286,
         offset_height_end=1, offset_width=0):
    """

    :param img:
    :param me:
    :param m:
    :param size:
    :param print_text:
    :param range_ids:
    :param output:
    :param offset_height:
    :param offset_height_end:
    :param offset_width:
    :return:
    """
    # Datetime
    now = datetime.now()
    send_message(now.strftime("%d/%m/%Y, %H:%M:%S"), messages)

    # Pixels per meter
    ppm = 420
    # Area to scan
    area_height = 1.05
    area_width = 1.20
    area_ratio = area_height / area_width
    # In cm
    center_width = 0.15

    # Resizing image
    if size is not None:
        img_resize = cv2.resize(img, size)
    else:
        img_resize = img

    # 75% - 100% : 1.333333
    # 55% - 100% : 1.818181
    half = round(img_resize.shape[0] // offset_height)
    # Middle point of image
    middle = img_resize.shape[1] // 2
    # Width of image
    w = img_resize.shape[1]
    padding_width = round(w * offset_width)
    # Height of image
    # h = img_resize.shape[0]
    h = round(img_resize.shape[0] // offset_height_end)
    # Left side of image
    img_left = img_resize[half:h, 0 + padding_width:middle]
    # Right side of image
    img_right = img_resize[half:h, middle:w - padding_width]

    f.draw_binding_box(img_resize, (0 + padding_width, half), (0 + padding_width, h), (w - padding_width, half),
                       (w - padding_width, h))

    c_x = int(w // 2)
    c_y = int(h // 2)

    # Aruco dictionary 4x4_50
    aruco_dict = cv2.aruco.Dictionary_get(cv2.aruco.DICT_4X4_250)
    # Aruco params
    aruco_params = cv2.aruco.DetectorParameters_create()
    # Reading aruco markers detected on the left side
    l_markers = f.draw_markers(img_left, img_resize, aruco_dict, aruco_params, 0 + padding_width, range_ids, half)
    # Reading aruco markers detected on the right side
    r_markers = f.draw_markers(img_right, img_resize, aruco_dict, aruco_params, middle, range_ids, half)

    if me is not None:
        send_message("Battery Level: " + str(me.get_battery()) + "%", messages)

    movements = [0, 0, 0, 0]

    ids = []

    # Distance
    if len(l_markers) == 1 and len(r_markers) == 1:
        p1 = l_markers[0][0]
        p2 = r_markers[0][0]
        ids = [l_markers[0][1], r_markers[0][1]]
        a1 = l_markers[0][2]
        a2 = r_markers[0][2]
        # Area Difference
        if a1 > 0 and a2 > 0:
            delta_area = (1 - a2/a1) * 100
        else:
            delta_area = 0
        # print(p1, " - ", p2)
        angle = get_angle_between_two_points(p1, p2)
        if print_text:
            f.put_text(img_resize, "Angle: " + str(round(angle, 2)) + " degrees", 600, 140)
        if delta_area != 0:
            if print_text:
                f.put_text(img_resize, "Delta Area: " + str(round(delta_area, 2)) + "%", 600, 170)
        distance = f.distance_in_meters(math.dist(p1, p2), ppm)
        # Delta yaw
        delta_d = int((distance - area_width) * 100)
        if print_text:
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
        if print_text:
            f.put_text(img_resize, "Delta X: " + str(int(delta_x)) + " cms", 600, 50)
            f.put_text(img_resize, "Delta Y: " + str(int(delta_y)) + " cms", 600, 80)
        # def movements(delta, delta_width, width_center, image):
        movements = f.movements((delta_x, delta_y), delta_d, center_width * 100, img_resize, print_text=print_text)
        # movements = [delta_x, delta_y, delta_d]
        send_message("Roll - Throttle - Pitch - Yaw: " + str(movements), messages)
        # If is in target
        if all(item == 0 for item in movements):
            result = "ON TARGET"
        else:
            result = "SUCCESS"
    else:
        result = "NOT FOUND"

    if m is None:
        m = []
    for message in m:
        send_message(message, messages)

    if print_text:
        print_messages(img_resize, messages)
    if output:
        cv2.imshow("Output", img_resize)

    # cv2.imshow("Left", img_left)
    # cv2.imshow("Right", img_right)

    return result, movements, img_resize, ids


def read_markers(img, me=None, m=None, size=None, _print=True, range_ids=None, offset_height=1.4286,
                 offset_height_end=1, offset_width=0):
    """

    :param img:
    :param me:
    :param m:
    :param size:
    :param _print:
    :param range_ids:
    :param offset_height:
    :param offset_height_end:
    :param offset_width: % of width (0 - 0.99)
    :return:
    """
    # Datetime
    now = datetime.now()
    send_message(now.strftime("%d/%m/%Y, %H:%M:%S"), messages)

    # Resizing image
    if size is not None:
        img_resize = cv2.resize(img, size)
    else:
        img_resize = img

    # 50% - 100%
    half = round(img_resize.shape[0] // offset_height)
    # Width of image
    w = img_resize.shape[1]
    padding_width = round(w * offset_width)
    # Height of image
    h = round(img_resize.shape[0] // offset_height_end)

    # Portion of original image to scan for ArUco markers
    img_markers = img_resize[half:h, (0 + padding_width):w - padding_width]

    f.draw_binding_box(img_resize, (0 + padding_width, half), (0 + padding_width, h), (w - padding_width, half),
                       (w - padding_width, h))

    # Aruco dictionary 4x4_50
    aruco_dict = cv2.aruco.Dictionary_get(cv2.aruco.DICT_4X4_250)
    # Aruco params
    aruco_params = cv2.aruco.DetectorParameters_create()
    # Reading aruco markers detected
    all_markers = f.draw_markers(img_markers, img_resize, aruco_dict, aruco_params, 0 + padding_width, range_ids, half)

    if me is not None:
        send_message("Battery Level: " + str(me.get_battery()) + "%", messages)

    result = "SUCCESS"

    if m is None:
        m = []
    for message in m:
        send_message(message, messages)

    if _print:
        print_messages(img_resize, messages)
    cv2.imshow("Output Markers", img_resize)

    return result, all_markers, img_resize
