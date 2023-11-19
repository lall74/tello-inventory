from djitellopy import tello
import frameProcessing as fp
import functions as f
import time
import configparser
import cv2
from datetime import datetime
from datetime import timedelta
from simple_pid import PID
import csv

# Parameters
config = configparser.ConfigParser()
config.read('config.ini')
general = config['GENERAL']
max_secs = config['MAX_SECS']
aruco_markers = config['ARUCO_MARKERS']
offset = config['OFFSET']

# Step
step = "IDLE"
step_go = "IDLE"
step_datetime_started = 0
step_secs = 0
level_marker = 0
side_marker = 0
err_message = ""
size = (1024, 768)

speed = general['Speed']
direction = "UP"
min_level = general['MinLevel']
max_level = general['MaxLevel']

max_secs_take_off = max_secs['TakeOff']
max_secs_focus = max_secs['Focus']
max_secs_take_picture = max_secs['TakePicture']
max_secs_find_directions = max_secs['FindDirections']
max_secs_next_location = max_secs['NextLocation']

# ArUco Marker Constants
odd_marker = aruco_markers['OddMarker']
even_marker = aruco_markers['EvenMarker']
markers_range = range(int(aruco_markers['MarkersRangeBegin']), int(aruco_markers['MarkersRangeEnd']))
level_markers_range = range(int(aruco_markers['LevelMarkersRangeBegin']), int(aruco_markers['LevelMarkersRangeBegin']))
directions_range = range(int(aruco_markers['DirectionsRangeBegin']), int(aruco_markers['DirectionsRangeBegin']))
numbers_range = range(int(aruco_markers['NumbersRangeBegin']), int(aruco_markers['NumbersRangeBegin']))

# 1.428571 : 70% - 100%   (100/70)
# 1.818181 : 55% - 100%   (100/55)
offset_height = offset['Height']
offset_width = offset['Width']
offset_height_end_focus = offset['HeightEndFocus']
offset_height_take_picture = offset['HeightTakePicture']
offset_height_end_take_picture = offset['HeightEndTakePicture']
offset_height_end_find_directions = offset['HeightEndFindDirections']
offset_width_find_directions = offset['WidthFindDirections']
offset_height_end_next_location = offset['HeightEndNextLocation']

# PID
# LEFT - RIGHT
pid_r = PID(1, 0.1, 0.05, setpoint=0, output_limits=(-10, 10))
# UP - DOWN
pid_t = PID(1, 0.1, 0.05, setpoint=0, output_limits=(-25, 5))
# BACKWARD - FORWARD
pid_p = PID(1, 0.1, 0.05, setpoint=0, output_limits=(-10, 10))

fp.ppm = 420
fp.area_height = 1.05
fp.area_width = 1.20
fp.center_width = 0.15

# Taking picture
# PARAM
# Flag to know if we get some markers or not...
markers = False

global_previous_error = [0, 0, 0]
# size = (2592, 1936)

messages = []
pause = False
autonomous = False
movements_from_image = None
# Todo: Include YAW
last_movements = [0, 0, 0]
last_manual_command = 0
mode = "MANUAL"
direction_msg = ""
time_started = time.time()
time_end = 0
# Datetime when we get on target
time_on_target = 0
# Amount of seconds continuously on target
secs_on_target = 0

now = datetime.now()
# Save on Video directory
prefix = now.strftime("Video/%Y%m%d%H%M%S")
prefix_output = now.strftime("Output/%Y%m%d%H%M%S")
prefix_result = now.strftime("Result/%Y%m%d%H%M%S")

img = None

fourcc = cv2.VideoWriter_fourcc(*'XVID')
out = cv2.VideoWriter(prefix + "_output.avi", fourcc, 20.0, size)
out_processed = cv2.VideoWriter(prefix + "_output_processed.avi", fourcc, 20.0, size)
out_csv = open(prefix_result + "_output_processed.csv", 'w')
csv_writer = csv.writer(out_csv)
csv_header = ['rack', 'columna', 'lado', 'nivel', 'identificador']
out_log = open(prefix + "_log.txt", "w")

csv_writer.writerow(csv_header)

print(speed, direction, min_level, max_level)

me = tello.Tello()
me.connect()
me.streamon()


def land():
    if me.is_flying:
        log("Land")
        messages.append("Land")
        me.land()


def end_flight():
    global time_end
    land()
    log("Stream off")
    messages.append("Stream OFF")
    # Set five seconds to exit loop and close windows
    time_end = time.time() + 5


def log(m):
    """
    :param m:
    :return:
    """
    global out_log
    n = datetime.now()
    text = n.strftime("%d/%m/%Y, %H:%M:%S:%f") + " " + str(m)
    print(text)
    out_log.write(text)
    out_log.write("\n")


def move(_me, _direction, _speed):
    """

    :param _me:
    :param _direction:
    :param _speed:
    :return:
    """
    log(f"MOVE: {_direction}... @ {_speed}")

    if _direction == "FORWARD":
        _me.send_rc_control(0, _speed, 0, 0)
    elif _direction == "BACKWARD":
        _me.send_rc_control(0, -_speed, 0, 0)
    elif _direction == "LEFT":
        _me.send_rc_control(-10, 0, 0, 0)
    elif _direction == "RIGHT":
        _me.send_rc_control(10, 0, 0, 0)
    elif _direction == "UP":
        _me.send_rc_control(0, 0, _speed, 0)
    elif _direction == "DOWN":
        _me.send_rc_control(0, 0, -_speed + 5, 0)
    elif _direction == "CLOCKWISE":
        _me.send_rc_control(0, 0, 0, _speed)
    elif _direction == "COUNTERCLOCKWISE":
        _me.send_rc_control(0, 0, 0, -_speed)
    elif _direction == "HOVER":
        _me.send_rc_control(0, 0, 0, 0)


def move_distance(_me, _direction, _distance):
    """

    :param _me:
    :param _direction:
    :param _distance:
    :return:
    """
    log(f"MOVE DISTANCE: {_direction}... @ {_distance}")

    if _direction == "FORWARD":
        _me.move_forward(_distance)
    elif _direction == "BACKWARD":
        _me.move_back(_distance)
    elif _direction == "LEFT":
        _me.move_left(_distance)
        # _me.send_rc_control(-5, 0, 0, 0)
    elif _direction == "RIGHT":
        _me.move_right(_distance)
        # _me.send_rc_control(5, 0, 0, 0)
    elif _direction == "UP":
        _me.move_up(_distance)
    elif _direction == "DOWN":
        _me.move_down(_distance)
    elif _direction == "CLOCKWISE":
        _me.rotate_clockwise(_distance)
    elif _direction == "COUNTERCLOCKWISE":
        _me.rotate_counter_clockwise(_distance)
    elif _direction == "HOVER":
        _me.send_rc_control(0, 0, 0, 0)


log("Battery Level: " + str(me.get_battery()) + "%")

rack = int(input('Enter rack number: '))
column = int(input('Enter column number: '))

while True:

    if time_end > 0:
        if time.time() > time_end:
            # Todo: Track statistics, time session, battery consumption, etc.
            me.streamoff()
            log("Bye")
            break

    if not pause:
        img = me.get_frame_read().frame
        try:
            img_resize = cv2.resize(img, size)
            # Recording original video resized
            out.write(img_resize)
        except BaseException as err:
            log(f"Unexpected {err=}, {type(err)=}")
            log(img.shape() + " - " + str(size))

    time.sleep(1 / 10)

    f.put_text(img_resize, mode + ": " + direction_msg, 50, 740, 0.75, color=(0, 255, 0))

    # Take off
    if step == 'TAKE_OFF':
        if step_datetime_started == 0:
            log("TAKE OFF START...")
            messages.append("TAKE OFF START...")
            step_datetime_started = time.time()
            direction = "UP"
            move(me, direction, speed)
            # move_distance(me, direction, 20)
            # time.sleep(1 / 10)
        elif step_datetime_started > 0:
            step_secs = round(time.time() - step_datetime_started)
        if step_secs > max_secs_take_off:
            err_message = "Max time to find markers after take off reached! Error"
            step = 'ABORT'
        else:
            # Looking for markers
            _, result_markers, result_img = fp.read_markers(img_resize, me, size=None, range_ids=markers_range,
                                                            offset_height=offset_height, offset_width=offset_width)
            img_resize = cv2.resize(result_img, size)
            f.put_text(img_resize, "TAKE OFF", 528, 50)
            if len(result_markers) > 0:
                log("MARKERS FOUND...")
                f.put_text(img_resize, "SUCCESS", 528, 80)
                f.img_write(prefix + "_TAKE_OFF", result_img)
                # Next step
                # Stop throttle
                move(me, "HOVER", 0)
                step = 'FOCUS'
                # Reset flags
                step_datetime_started = 0
                step_secs = 0
            else:
                f.put_text(img_resize, "NOT FOUND", 528, 80)
                # move_distance(me, direction, 20)
                # time.sleep(1 / 10)
    elif step == 'FOCUS' or step == "FOCUS_AND_GO":
        if step_datetime_started == 0:
            log("FOCUS START...")
            messages.append("FOCUS START...")
            step_datetime_started = time.time()
            global_previous_error = [0, 0, 0]
            step_secs = 0
        elif step_datetime_started > 0:
            step_secs = round(time.time() - step_datetime_started)
        if step_secs > max_secs_focus:
            err_message = "Max time to focus location reached! Error"
            step = 'ABORT'
        else:
            # Processing frame
            """
            Values for result
                SUCCESS: Found markers, but need adjustment
                NOT FOUND: No markers was found
                ON TARGET: Found markers and is in position to take picture and it's ready to continue with the next position
            """
            result, movements_from_image, img_resize, ids = fp.read(img_resize, me, m=messages, range_ids=markers_range,
                                                                    offset_height=offset_height,
                                                                    offset_height_end=offset_height_end_focus,
                                                                    offset_width=offset_width)
            messages.clear()
            messages.append("Time on Target: " + str(timedelta(seconds=secs_on_target)))
            messages.append("Time Elapsed: " + str(timedelta(seconds=int(time.time() - time_started))))

            f.put_text(img_resize, "FOCUS", 528, 740)

            if result == "SUCCESS" or result == "ON TARGET":
                # Current level marker
                if ids[0] in level_markers_range:
                    level_marker = ids[0]
                elif ids[0] in (odd_marker, even_marker):
                    side_marker = ids[0]
                # Current side marker
                if ids[1] in level_markers_range:
                    level_marker = ids[1]
                elif ids[1] in (odd_marker, even_marker):
                    side_marker = ids[1]

            # Drone movement only if return success
            if result == "SUCCESS":
                # ToDo: Try to consider a tolerance
                time_on_target = 0
                secs_on_target = 0
                """
                0: Roll
                1: Throttle
                2: Pitch
                """
                result = f.roll_throttle_pitch_v3(movements_from_image[0], movements_from_image[1],
                                                  movements_from_image[2],
                                                  global_previous_error, pid_r, pid_t, pid_p)
                # ToDo: Include YAW in parameters
                global_previous_error = result[3]

                messages.append("SIDE MARKERS: " + str(level_marker) + " - " + str(side_marker))

                if autonomous:
                    # log(result)
                    # ToDo: What happen if value is 0 0 0 0 ?
                    if not f.list_are_equals(result[0:3], last_movements):
                        #
                        # me.send_rc_control(roll, pitch, throttle, 0)
                        """
                        result:
                        0: Roll
                        1: Throttle
                        2: Pitch
                        3: Previous errors
                        Parameters for send_rc_control
                        1: left_right_velocity (Roll)
                        2: forward_backward_velocity (Pitch)
                        3: up_down_velocity (Throttle)
                        4: yaw_velocity (Yaw)
                        """
                        # Changed for move_distance
                        # me.send_rc_control(result[0], -result[2], -result[1], 0)

                        message = ""
                        """
                        Roll
                        If the difference is positive, we are focusing to the left of our target, 
                            so we need to go to the right (positive speed)
                        If the difference is negative, we are focusing to the right of our target, 
                            so we need to go to the left (negative speed)
                        """
                        if result[0] > 0:
                            message += " RIGHT: " + str(result[0])
                            move_distance(me, "RIGHT", 20)
                        elif result[0] < 0:
                            message += " LEFT: " + str(result[0])
                            move_distance(me, "LEFT", 20)
                        else:
                            message += " HOVER "
                        """
                        Throttle
                        If the difference is positive, we are focusing above our target, 
                            so we need to go down (negative speed)
                        If the difference is negative, we are focusing below our target, 
                            so we need to go up (positive speed)
                        """
                        if result[1] > 0:
                            message += " DOWN: " + str(-result[1])
                            move_distance(me, "DOWN", 20)
                        elif result[1] < 0:
                            message += " UP: " + str(-result[1])
                            move_distance(me, "UP", 20)
                        else:
                            message += " HOVER "
                        """
                        Pitch
                        If the difference is positive, we are too close to our target, 
                            so we need to get away (negative speed)
                        If the difference is negative, we are far from our target, 
                            so we need to get closer (positive speed)
                        """
                        if result[2] > 0:
                            message += " BACKWARD: " + str(-result[2])
                            move_distance(me, "BACKWARD", 20)
                        elif result[2] < 0:
                            message += " FORWARD: " + str(-result[2])
                            move_distance(me, "FORWARD", 20)
                        else:
                            message += " HOVER "
                        direction_msg = message
                        log("MODE: AUTONOMOUS " + message)
                        messages.append("MODE: AUTONOMOUS " + message)
                        # ToDo: Consider YAW parameter
                        last_movements = result[0:3]
                else:
                    messages.append("MODE: MANUAL")
            elif result == "ON TARGET":
                # Taking picture
                log("On target")
                messages.append("ON TARGET")
                if step == "FOCUS_AND_GO":
                    step = step_go
                    if step == 'NEXT_LOCATION':
                        move(me, direction, speed)
                        # move_distance(me, direction, 20)
                        # time.sleep(1 / 10)
                    else:
                        move(me, "HOVER", 0)
                else:
                    step = 'TAKE_PICTURE'
                    move(me, "HOVER", 0)
                # Reset flags
                step_datetime_started = 0
                step_secs = 0
                # me.send_rc_control(0, 0, 0, 0)
    # Taking picture
    elif step == 'TAKE_PICTURE':
        # me.send_rc_control(0, 0, 0, 0)
        if step_datetime_started == 0:
            log("TAKE PICTURE START...")
            messages.append("TAKE PICTURE START...")
            step_datetime_started = time.time()
            markers = False
            # HOVER since FOCUS and ON TARGET event...
            # move(me, "HOVER", 0)
        elif step_datetime_started > 0:
            step_secs = round(time.time() - step_datetime_started)
        # Finding number markers...
        _, number_markers, numbers_img = fp.read_markers(img, size=None, _print=True, range_ids=numbers_range,
                                                         offset_height=offset_height_take_picture,
                                                         offset_height_end=offset_height_end_take_picture,
                                                         offset_width=offset_width)
        img_resize = cv2.resize(numbers_img, size)
        f.put_text(img_resize, "TAKE PICTURE", 528, 50)
        # If we get four markers
        if len(number_markers) == 4:
            f.put_text(img_resize, "SUCCESS", 528, 80)
            f.img_write(prefix_result + "_INFO", numbers_img)
            step = 'FOCUS_AND_GO'
            step_go = 'FIND_DIRECTIONS'
            # Reset flags
            step_datetime_started = 0
            step_secs = 0
            markers = False
            r = ""
            identifier = ""
            for m in number_markers:
                if r == "":
                    r += str(m[1])
                else:
                    r = r + " - " + str(m[1])
                identifier += str(m[1])
            f.put_text(img_resize, r, 528, 110)
            csv_data = [rack, column, side_marker, level_marker, identifier]
            csv_writer.writerow(csv_data)
        else:
            # If we found some markers ..
            if len(number_markers) > 0:
                markers = True
            else:
                f.put_text(img_resize, "NOT FOUND", 528, 80)
            if step_secs > max_secs_take_picture:
                if markers:
                    # If there is at least one marker, result = ERROR_READING
                    err_message = "Cannot get four markers! Error"
                    suffix = "_ERROR"
                    f.put_text(img_resize, "SCAN INCOMPLETE", 528, 110)
                else:
                    # If there is no markers, result = EMPTY
                    err_message = "Number markers not found! Empty Location"
                    suffix = "_EMPTY"
                    f.put_text(img_resize, "LOCATION EMPTY", 528, 110)
                # Stop looking for number markers...
                f.img_write(prefix_result + suffix, numbers_img)
                step = 'FOCUS_AND_GO'
                step_go = 'FIND_DIRECTIONS'
                # Reset flags
                step_datetime_started = 0
                step_secs = 0
                markers = False
    elif step == 'FIND_DIRECTIONS':
        # me.send_rc_control(0, 0, 0, 0)
        if step_datetime_started == 0:
            log("FIND DIRECTIONS START...")
            messages.append("FIND DIRECTIONS START...")
            step_datetime_started = time.time()
        elif step_datetime_started > 0:
            step_secs = round(time.time() - step_datetime_started)
        if step_secs > max_secs_find_directions:
            f.put_text(img_resize, "CONTINUE", 528, 80)
            err_message = "Max time to find directions reached! Continue"
            log(err_message)
            step = 'FOCUS_AND_GO'
            step_go = 'NEXT_LOCATION'
            # Start movement with the same direction...
            # move(me, direction, speed) @FOCUS_AND_GO
            # Reset flags
            step_datetime_started = 0
            step_secs = 0
        else:
            # Finding change direction markers...
            _, direction_markers, directions_img = fp.read_markers(img, size=None, _print=True,
                                                                   range_ids=directions_range,
                                                                   offset_height=offset_height,
                                                                   offset_height_end=offset_height_end_find_directions,
                                                                   offset_width=offset_width_find_directions)
            img_resize = cv2.resize(directions_img, size)
            f.put_text(img_resize, "FIND DIRECTIONS", 528, 50)
            # If we get one marker
            if len(direction_markers) == 1:
                if direction_markers[0][1] == 11:
                    direction = "UP"
                elif direction_markers[0][1] == 12:
                    direction = "DOWN"
                elif direction_markers[0][1] == 13:
                    direction = "LEFT"
                elif direction_markers[0][1] == 14:
                    direction = "RIGHT"
                elif direction_markers[0][1] == 15:
                    direction = "LAND"
                f.img_write(prefix_result + "_DIRECTIONS", directions_img)
                if direction == "LAND":
                    f.put_text(img_resize, "LANDING...", 528, 80)
                    step = 'END'
                    direction = "HOVER"
                else:
                    step = 'FOCUS_AND_GO'
                    step_go = 'NEXT_LOCATION'
                    f.put_text(img_resize, "MOVE " + direction, 528, 80)
                    # move(me, direction, speed)
                # Reset flags
                step_datetime_started = 0
                step_secs = 0
            else:
                f.put_text(img_resize, "NOT FOUND", 528, 80)
    elif step == 'NEXT_LOCATION':
        # me.send_rc_control(0, 0, 0, 0)
        if step_datetime_started == 0:
            log("NEXT LOCATION START...")
            step_datetime_started = time.time()
            # Move to previous step...
            # move(me, direction, speed)
            step_secs = 0
        elif step_datetime_started > 0:
            step_secs = round(time.time() - step_datetime_started)
        if step_secs > max_secs_next_location:
            err_message = "Max time to find next location reached! Error"
            step = 'ABORT'
        else:
            next_location_range = None
            if direction == "UP":
                if level_marker < max_level:
                    next_location_range = range(level_marker + 1, level_marker + 2)
                else:
                    err_message = "Max level reached! - next_location_range"
                    step = "ABORT"
            elif direction == "DOWN":
                if level_marker > min_level:
                    next_location_range = range(level_marker - 1, level_marker)
                else:
                    err_message = "Min level reached! - next_location_range"
                    step = "ABORT"
            elif direction == "LEFT" or direction == "RIGHT":
                if side_marker == even_marker:
                    next_location_range = range(odd_marker, odd_marker + 1)
                else:
                    next_location_range = range(even_marker, even_marker + 1)
            # log(next_location_range)
            if next_location_range is None:
                err_message = "Error finding next location - next_location_range"
                step = "ABORT"
            else:
                _, next_location_markers, next_location_img = fp.read_markers(img, size=None, _print=True,
                                                                              range_ids=next_location_range,
                                                                              offset_height=offset_height,
                                                                              offset_height_end=offset_height_end_next_location,
                                                                              offset_width=offset_width)
                img_resize = cv2.resize(next_location_img, size)
                f.put_text(img_resize, "NEXT LOCATION", 528, 50)
                if len(next_location_markers) == 1:
                    f.put_text(img_resize, "SUCCESS", 528, 80)
                    step = "FOCUS"
                    f.img_write(prefix_result + "_NEXT_LOCATION", next_location_img)
                    # Reset flags
                    step_datetime_started = 0
                    step_secs = 0
                    # Stop movement
                    move(me, "HOVER", 0)
                else:
                    f.put_text(img_resize, "NOT FOUND", 528, 80)
                    # move_distance(me, direction, 20)
    elif step == 'ABORT':
        log("ABORT")
        log(err_message)
        end_flight()
        step = "IDLE"
    elif step == 'END':
        log("END")
        end_flight()
        step = "IDLE"

    if not autonomous:
        # Processing frame
        """
        Values for result
            SUCCESS: Found markers, but need adjustment
            NOT FOUND: No markers was found
            ON TARGET: Found markers and is in position to take picture and it's ready to continue with the next position
        """
        result, movements_from_image, img_resize, ids = fp.read(img_resize, me, m=messages, range_ids=markers_range,
                                                                offset_height=offset_height, offset_width=offset_width)
        messages.clear()
        messages.append("Time on Target: " + str(timedelta(seconds=secs_on_target)))
        messages.append("Time Elapsed: " + str(timedelta(seconds=int(time.time() - time_started))))

        # Drone movement only if return success
        if result == "SUCCESS":
            # ToDo: Try to consider a tolerance
            time_on_target = 0
            secs_on_target = 0
            """
            0: Roll
            1: Throttle
            2: Pitch
            """
            result = f.roll_throttle_pitch_v3(movements_from_image[0], movements_from_image[1],
                                              movements_from_image[2],
                                              global_previous_error, pid_r, pid_t, pid_p)

            # ToDo: Include YAW in parameters
            global_previous_error = result[3]

            # Current level marker
            if ids[0] in level_markers_range:
                level_marker = ids[0]
            elif ids[0] in (odd_marker, even_marker):
                side_marker = ids[0]
            # Current side marker
            if ids[1] in level_markers_range:
                level_marker = ids[1]
            elif ids[1] in (odd_marker, even_marker):
                side_marker = ids[1]

            messages.append("SIDE MARKERS: " + str(level_marker) + " - " + str(side_marker))

        elif result == "ON TARGET":
            # Taking picture
            log("On target")
            messages.append("ON TARGET")
            step = 'TAKE_PICTURE'
            # Reset flags
            step_datetime_started = 0
            step_secs = 0

    cv2.imshow("Output", img_resize)

    # Recording video processed
    out_processed.write(img_resize)

    time.sleep(1 / 10)

    k = cv2.waitKeyEx(1)

    # me.send_rc_control
    # left_right_velocity - forward_backward_velocity - up_down_velocity - yaw_velocity
    # Manual commands...
    if k == -1:
        continue
    elif k == 32:
        # Pause and continue
        log("Pause")
        messages.append("PAUSE")
        pause = not pause
    elif k == ord('y') or k == ord('Y'):
        # Autonomous
        log("Autonomous ON")
        messages.append("Autonomous ON")
        mode = "AUTONOMOUS"
        autonomous = True
        step = "TAKE_OFF"
    elif k == ord('x') or k == ord('X'):
        # Autonomous
        log("Autonomous OFF")
        messages.append("Autonomous OFF")
        mode = "MANUAL"
        autonomous = False
        step = "IDLE"
    elif k == ord('l') or k == ord('L') or k == 2293760:
        # Just landing key l or End (Fin)
        step = 'IDLE'
        land()
    elif k == ord('q') or k == ord('Q') or k == 27:
        # End flight
        autonomous = False
        step = 'END'
        # end_flight()
    elif k == 2359296:
        # Home (Inicio)
        log("Take off")
        # step = 'TAKE_OFF'
        messages.append("Take off")
        me.takeoff()
    elif k == ord('0'):
        # Keypad 0
        me.send_rc_control(0, 0, 0, 0)
        log("Stop")
        direction_msg = "HOVER"
        messages.append(direction_msg)
        step = "IDLE"
    elif k == ord('p') or k == ord('P'):
        f.img_write(prefix_output, img)
        prefix_output = now.strftime("Output/%Y%m%d%H%M%S")
    else:
        # Manual movements...
        if k != last_manual_command:
            if k == 2490368:
                # Up Arrow
                # me.send_rc_control(0, speed, 0, 0)
                me.move_forward(20)
                log("Forward")
                direction_msg = "FORWARD"
                messages.append(direction_msg)
                last_manual_command = k
            elif k == 2621440:
                # Down Arrow
                # me.send_rc_control(0, -speed, 0, 0)
                me.move_back(20)
                log("Backward")
                direction_msg = "BACKWARD"
                messages.append(direction_msg)
                last_manual_command = k
            elif k == 2424832:
                # Left Arrow
                # me.send_rc_control(-speed, 0, 0, 0)
                me.move_left(20)
                log("Left")
                direction_msg = "LEFT"
                messages.append(direction_msg)
                last_manual_command = k
            elif k == 2555904:
                # Right Arrow
                # me.send_rc_control(speed, 0, 0, 0)
                me.move_right(20)
                log("Right")
                direction_msg = "RIGHT"
                messages.append(direction_msg)
                last_manual_command = k
            elif k == ord('w') or k == ord('W'):
                # Key K
                # me.send_rc_control(0, 0, speed, 0)
                me.move_up(20)
                log("Up")
                direction_msg = "UP"
                messages.append(direction_msg)
                last_manual_command = k
            elif k == ord('s') or k == ord('S'):
                # Key S
                # me.send_rc_control(0, 0, -speed, 0)
                me.move_down(20)
                log("Down")
                direction_msg = "DOWN"
                messages.append(direction_msg)
                last_manual_command = k
            elif k == ord('a') or k == ord('A'):
                # Key A
                # me.send_rc_control(0, 0, 0, speed)
                me.rotate_clockwise(15)
                log("Turn clockwise")
                direction_msg = "TURN CLOCKWISE"
                messages.append(direction_msg)
                last_manual_command = k
            elif k == ord('d') or k == ord('D'):
                # Key D
                # me.send_rc_control(0, 0, 0, -speed)
                me.rotate_counter_clockwise(15)
                log("Turn counterclockwise")
                direction_msg = "TURN COUNTERCLOCKWISE"
                messages.append(direction_msg)
                last_manual_command = k
        else:
            log(str(k))

config.release()
out.release()
out_processed.release()
out_log.close()
out_csv.close()
cv2.destroyAllWindows()
