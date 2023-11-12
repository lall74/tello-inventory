import cv2
import numpy
import functools
from datetime import datetime
from simple_pid import PID

pid = [0.4, 0.4, 0]
pid2 = [0.4, 0.4, 0]


def put_text(image, message, x, y, size=1, thickness=2, color=(255, 255, 0)):
    """

    :param image:
    :param message:
    :param x:
    :param y:
    :param size:
    :param thickness:
    :param color:
    :return:
    """
    cv2.putText(image, message, (x, y), cv2.FONT_HERSHEY_SIMPLEX, size, color, thickness)


def distance_in_meters(dist, ppm):
    """

    :param dist:
    :param ppm:
    :return:
    """
    if dist != 0:
        return dist / ppm
    else:
        return 0.0


def log(m):
    """

    :param m:
    :return:
    """
    now = datetime.now()
    print(now.strftime("%d/%m/%Y, %H:%M:%S") + " " + str(m))


def list_are_equals(l1, l2):
    return functools.reduce(lambda x, y: x and y, map(lambda p, q: p == q, l1, l2), True)


def distance_in_pixels(dist, ppm):
    """

    :param dist:
    :return:
    """
    return dist * ppm


def get_corners(marker_corner, offset=0, offset_height=0):
    """

    :param marker_corner:
    :param offset:
    :param offset_height:
    :return:
    """
    corners = marker_corner.reshape((4, 2))
    (top_left, top_right, bottom_right, bottom_left) = corners
    top_right = (int(top_right[0]) + offset, int(top_right[1]) + offset_height)
    bottom_right = (int(bottom_right[0]) + offset, int(bottom_right[1]) + offset_height)
    bottom_left = (int(bottom_left[0]) + offset, int(bottom_left[1]) + offset_height)
    top_left = (int(top_left[0]) + offset, int(top_left[1]) + offset_height)

    return top_left, top_right, bottom_left, bottom_right


def draw_binding_box(image, top_left, top_right, bottom_left, bottom_right, color=(0, 255, 0)):
    """

    :param image:
    :param top_left:
    :param top_right:
    :param bottom_left:
    :param bottom_right:
    :param color:
    :return:
    """
    cv2.line(image, top_left, top_right, color, 2)
    cv2.line(image, top_right, bottom_right, color, 2)
    cv2.line(image, bottom_right, bottom_left, color, 2)
    cv2.line(image, bottom_left, top_left, color, 2)


def area_polygon(polygon):
    """

    :param polygon:
    :return:
    """
    a = 0
    for i in range(0, len(polygon) - 1):
        p1 = polygon[i - 1]
        p2 = polygon[i]
        b = (p2[1] + p1[1]) / 2
        h = p2[0] - p1[0]
        a += b * h
    # print("Area of: ", polygon, " is: ", a)
    return a


def draw_binding_boxes(image, corners, ids, offset, range_ids=None, offset_height=0):
    """

    :param image:
    :param corners:
    :param ids:
    :param offset:
    :param range_ids:
    :param offset_height:
    :return:
    """
    result = []
    for (marker_corner, marker_id) in zip(corners, ids):
        """
        Filtering
        1: Level and size markers
        2: Direction markers
        3: Numeric markers
        """
        include = False
        if range_ids is None:
            include = True
        elif marker_id in range_ids:
            include = True

        if include:
            (top_left, top_right, bottom_left, bottom_right) = get_corners(marker_corner, offset, offset_height)
            # Draw binding box
            draw_binding_box(image, top_left, top_right, bottom_left, bottom_right)
            x = int((top_left[0] + bottom_right[0]) // 2)
            y = int((top_left[1] + bottom_right[1]) // 2)
            cv2.circle(image, (x, y), 4, (0, 0, 255), -1)
            # (x, y) coordinates, marker id, area
            result.append([[x, y], marker_id, area_polygon([top_left, top_right, bottom_right, bottom_left])])
    return result


def draw_markers(image_source, image, dictionary, params, offset, range_ids=None, offset_height=0):
    """

    :param image_source:
    :param image:
    :param dictionary:
    :param params:
    :param offset:
    :param range_ids:
    :param offset_height:
    :return:
    """
    result = []
    (corners, ids, rejected) = cv2.aruco.detectMarkers(image_source, dictionary, parameters=params)
    # If aruco markers found
    if len(corners) > 0:
        ids = ids.flatten()
        # Loop through the detected ArUco corners
        result = draw_binding_boxes(image, corners, ids, offset, range_ids, offset_height)
    return result


def draw_rectangle(image, bottom_left, bottom_right, height, reference_point, width_center):
    """

    :param image:
    :param bottom_left:
    :param bottom_right:
    :param height:
    :param reference_point:
    :param width_center:
    :return:
    """
    top_left = (bottom_left[0], int(bottom_left[1] - height))
    top_right = (bottom_right[0], int(bottom_right[1] - height))
    draw_binding_box(image, top_left, top_right, bottom_left, bottom_right)
    c_x = int((top_left[0] + bottom_right[0]) / 2.0)
    c_y = int((top_left[1] + bottom_right[1]) / 2.0)
    # Draw a line between points
    cv2.line(image, reference_point, (c_x, c_y), (0, 255, 0), 2)
    # Draw center of reference_point
    cv2.circle(image, reference_point, 6, (255, 255, 0), -1)
    # Draw center of rectangle
    cv2.circle(image, (c_x, c_y), 6, (0, 0, 255), -1)
    # Center area
    top_left = (int(reference_point[0] - width_center), int(reference_point[1] - width_center))
    top_right = (int(reference_point[0] + width_center), int(reference_point[1] - width_center))
    bottom_left = (int(reference_point[0] - width_center), int(reference_point[1] + width_center))
    bottom_right = (int(reference_point[0] + width_center), int(reference_point[1] + width_center))
    # print(reference_point, ":", width_center, ":", top_left, "-", top_right, "-", bottom_left, "-", bottom_right)
    draw_binding_box(image, top_left, top_right, bottom_left, bottom_right, color=(255, 255, 0))
    # Delta
    delta_x = int(c_x - reference_point[0])
    delta_y = int(c_y - reference_point[1])
    return delta_x, delta_y


def move_right_left(distance):
    """

    :param distance:
    :return:
    """


def movements(delta, delta_width, width_center, image, print_text=True):
    """

    :param delta:
    :param delta_width:
    :param width_center:
    :param image:
    :param print_text:
    :return:
    """
    roll = 0
    throttle = 0
    pitch = 0
    yaw = 0
    messages = []

    if delta[0] > width_center or delta[0] < -width_center:
        roll = delta[0]
        if roll > 0:
            messages.append("Move RIGHT")
        elif roll < 0:
            messages.append("Move LEFT")

    if delta[1] > width_center or delta[1] < -width_center:
        throttle = delta[1]
        if throttle > 0:
            messages.append("Move DOWN")
        elif throttle < 0:
            messages.append("Move UP")

    if delta_width > width_center or delta_width < -width_center:
        pitch = int(delta_width)
        if pitch > 0:
            messages.append("Move BACKWARD")
        elif pitch < 0:
            messages.append("Move FORWARD")

    i = 0
    if print_text:
        for message in messages:
            cv2.putText(image, message, (50, 50 + i * 40), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 0), 2)
            i += 1

    return [roll, throttle, pitch, yaw]


def roll_throttle_pitch(roll, throttle, pitch, previous_error):
    """

    :param roll:
    :param throttle:
    :param pitch:
    :param pid:
    :param previous_error:
    :return:
    """

    max_speed = 20
    # Method PID for speed
    # Roll (LEFT - RIGHT)
    if roll != 0:
        error = roll
        speed = pid[0] * error + pid[1] * (error - previous_error[0])
        roll = int(numpy.clip(speed, -max_speed, max_speed))
        previous_error[0] = error
    else:
        previous_error[0] = 0

    # Throttle (UP - DOWN)
    if throttle != 0:
        error = throttle
        speed = pid2[0] * error + pid2[1] * (error - previous_error[1])
        throttle = int(numpy.clip(speed, -max_speed, max_speed))
        previous_error[1] = error
    else:
        previous_error[1] = 0

    # Pitch (FORWARD - BACKWARD)
    if pitch != 0:
        error = pitch
        speed = pid[0] * error + pid[1] * (error - previous_error[2])
        pitch = int(numpy.clip(speed, -max_speed, max_speed))
        previous_error[2] = error
    else:
        previous_error[2] = 0

    return [roll, throttle, -pitch, previous_error]


def roll_throttle_pitch_v2(roll, throttle, pitch, previous_error, max_speed=10):
    """

    :param roll:
    :param throttle:
    :param pitch:
    :param previous_error:
    :param max_speed:
    :return:
    """

    # Method PID for speed
    # Pitch (FORWARD - BACKWARD)
    if pitch != 0:
        error = pitch
        speed = pid[0] * error + pid[1] * (error - previous_error[2])
        if speed > 0:
            pitch = int(numpy.clip(speed, 1, max_speed))
        else:
            pitch = int(numpy.clip(speed, -max_speed, -1))
        previous_error[2] = error
        roll = 0
        throttle = 0
        previous_error[0] = 0
        previous_error[1] = 0
    else:
        previous_error[2] = 0
        # Roll (LEFT - RIGHT)
        if roll != 0:
            error = roll
            speed = pid[0] * error + pid[1] * (error - previous_error[0])
            if speed > 0:
                # 10
                roll = int(numpy.clip(speed, 5, max_speed))
            else:
                # -10
                roll = int(numpy.clip(speed, -max_speed, -5))
            previous_error[0] = error
        else:
            previous_error[0] = 0

        # Throttle (UP - DOWN)
        if throttle != 0:
            error = throttle
            speed = pid2[0] * error + pid2[1] * (error - previous_error[1])
            if speed > 0:
                # Adjust by -10 for long distances
                # throttle = int(numpy.clip(speed, -max_speed, max_speed - 10))
                throttle = int(numpy.clip(speed, 5, max_speed - 5))
            else:
                # Adjust by -18 for long distances
                throttle = int(numpy.clip(speed, -max_speed - 0, -9))
            previous_error[1] = error
        else:
            previous_error[1] = 0

    return [roll, throttle, pitch, previous_error]


def roll_throttle_pitch_v3(roll, throttle, pitch, previous_error, pid_r, pid_t, pid_p):
    """

    :param roll:
    :param throttle:
    :param pitch:
    :param previous_error:
    :param pid_r:
    :param pid_t:
    :param pid_p:
    :return:
    """

    # Pitch (FORWARD - BACKWARD)
    if pitch != 0:
        error = pitch
        speed = pid_p(abs(error))
        if error > 0:
            pitch = -speed
        else:
            pitch = speed
        previous_error[0] = 0
        previous_error[1] = 0
        previous_error[2] = error
        roll = 0
        throttle = 0
    else:
        # Roll (LEFT - RIGHT)
        if roll != 0:
            error = roll
            speed = pid_r(abs(error))
            if error > 0:
                roll = -speed
            else:
                roll = speed
            previous_error[0] = error
            previous_error[1] = 0
            previous_error[2] = 0
            throttle = 0
            pitch = 0
        else:
            # Throttle (UP - DOWN)
            if throttle != 0:
                error = throttle
                speed = pid_t(abs(error))
                if error > 0:
                    throttle = -speed
                else:
                    throttle = speed
                roll = 0
                pitch = 0
            else:
                previous_error[0] = 0
                previous_error[1] = 0
                previous_error[2] = 0
                roll = 0
                throttle = 0
                pitch = 0

    return [roll, throttle, pitch, previous_error]


def img_write(prefix, img):
    """

    :param prefix:
    :param img:
    :return:
    """
    cv2.imwrite(prefix + "_output.png", img)
