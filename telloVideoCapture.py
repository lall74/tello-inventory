from djitellopy import tello
import frameProcessing as fp
import functions as f
import time
import cv2
from datetime import datetime
from datetime import timedelta

global_previous_error = [0, 0, 0]
size = (1024, 768)

messages = []
pause = False
autonomous = False
movements_from_image = None
# Todo: Include YAW
last_movements = [0, 0, 0]
last_manual_command = 0
mode = "MANUAL"
direction = ""
time_started = time.time()
time_end = 0
# Datetime when we get on target
time_on_target = 0
# Amount of seconds continuously on target
secs_on_target = 0

speed = 20
me = tello.Tello()
me.connect()
me.streamon()

now = datetime.now()
# Save on Video directory
prefix = now.strftime("Video/%Y%m%d%H%M%S")

fourcc = cv2.VideoWriter_fourcc(*'XVID')
out = cv2.VideoWriter(prefix + "_output.avi", fourcc, 20.0, size)
out_processed = cv2.VideoWriter(prefix + "_output_processed.avi", fourcc, 20.0, size)
out_log = open(prefix + "_log.txt", "w")


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
    me.streamoff()
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


log("Battery Level: " + str(me.get_battery()) + "%")

while True:

    if time_end > 0:
        if time.time() > time_end:
            # Todo: Track statistics, time session, battery consumption, etc.
            log("Bye")
            break

    if not pause:
        img = me.get_frame_read().frame
        try:
            img_resize = cv2.resize(img, size)
        except BaseException as err:
            log(f"Unexpected {err=}, {type(err)=}")
            log(img.shape() + " - " + str(size))

    # Recording original video resized
    out.write(img_resize)

    time.sleep(1 / 10)

    f.put_text(img_resize, mode + ": " + direction, 50, 740, 0.75, color=(0, 255, 0))

    # Processing frame
    """
    Values for result
        SUCCESS: Found markers, but need adjustment
        NOT FOUND: No markers was found
        ON TARGET: Found markers and is in position to take picture and is ready to continue with the next position
    """
    result, movements_from_image, img_resize = fp.read(img_resize, me, m=messages)
    messages.clear()
    messages.append("Time on Target: " + str(timedelta(seconds=secs_on_target)))
    messages.append("Time Elapsed: " + str(timedelta(seconds=int(time.time() - time_started))))

    # Recording video processed
    out_processed.write(img_resize)

    # Drone movement only if return success
    if result == "SUCCESS":
        # ToDo: Try to consider a tolerance
        time_on_target = 0
        secs_on_target = 0
        # log(result)
        result = f.roll_throttle_pitch_v2(movements_from_image[0], movements_from_image[1], movements_from_image[2],
                                          global_previous_error)
        # ToDo: Include YAW in parameters
        global_previous_error = result[3]

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
                me.send_rc_control(result[0], -result[2], -result[1], 0)
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
                elif result[0] < 0:
                    message += " LEFT: " + str(result[0])
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
                elif result[1] < 0:
                    message += " UP: " + str(-result[1])
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
                elif result[2] < 0:
                    message += " FORWARD: " + str(-result[2])
                else:
                    message += " HOVER "
                direction = message
                log("MODE: AUTONOMOUS " + message)
                messages.append("MODE: AUTONOMOUS " + message)
                # ToDo: Consider YAW parameter
                last_movements = result[0:3]
        else:
            messages.append("MODE: MANUAL")
    elif result == "ON TARGET":
        # Take picture and Land
        log("On target")
        messages.append("ON TARGET")
        if time_on_target == 0:
            time_on_target = time.time()
            secs_on_target = 0
        elif time_on_target > 0:
            secs_on_target = round(time.time() - time_on_target)
        # For now,
        if secs_on_target > 8:
            """
            If we have more than eight seconds, we assume there was a problem after reaching the target
            and reset counter
            """
            log("Time on target exceeded!")
            secs_on_target = 0
            time_on_target = 0
        elif secs_on_target > 5:
            # if we get five seconds on target, we land
            log("Time on target completed!, Good job!")
            end_flight()

    time.sleep(1 / 10)

    k = cv2.waitKeyEx(1)

    # me.send_rc_control
    # left_right_velocity - forward_backward_velocity - up_down_velocity - yaw_velocity

    if k == -1:
        continue
    elif k == 32:
        # Pause and continue
        log("Pause")
        messages.append("PAUSE")
        pause = not pause
    elif k == ord('y'):
        # Autonomous
        log("Autonomous ON")
        messages.append("Autonomous ON")
        mode = "AUTONOMOUS"
        autonomous = True
    elif k == ord('x'):
        # Autonomous
        log("Autonomous OFF")
        messages.append("Autonomous OFF")
        autonomous = False
        mode = "MANUAL"
    elif k == ord('l') or k == 2293760:
        # Just landing key l or End (Fin)
        land()
    elif k == ord('q') or k == 27:
        # End flight
        autonomous = False
        end_flight()
    elif k == 2359296:
        # Home (Inicio)
        log("Take off")
        messages.append("Take off")
        me.takeoff()
    elif k == ord('0'):
        # Keypad 0
        me.send_rc_control(0, 0, 0, 0)
        log("Stop")
        direction = "HOVER"
        messages.append(direction)
    else:
        if k != last_manual_command:
            if k == 2490368:
                # Up Arrow
                me.send_rc_control(0, speed, 0, 0)
                log("Forward")
                direction = "FORWARD"
                messages.append(direction)
                last_manual_command = k
            elif k == 2621440:
                # Down Arrow
                me.send_rc_control(0, -speed, 0, 0)
                log("Backward")
                direction = "BACKWARD"
                messages.append(direction)
                last_manual_command = k
            elif k == 2424832:
                # Left Arrow
                me.send_rc_control(-speed, 0, 0, 0)
                log("Left")
                direction = "LEFT"
                messages.append(direction)
                last_manual_command = k
            elif k == 2555904:
                # Right Arrow
                me.send_rc_control(speed, 0, 0, 0)
                log("Right")
                direction = "RIGHT"
                messages.append(direction)
                last_manual_command = k
            elif k == ord('w'):
                # Key K
                me.send_rc_control(0, 0, speed, 0)
                log("Up")
                direction = "UP"
                messages.append(direction)
                last_manual_command = k
            elif k == ord('s'):
                # Key S
                me.send_rc_control(0, 0, -speed, 0)
                log("Down")
                direction = "DOWN"
                messages.append(direction)
                last_manual_command = k
            elif k == ord('a'):
                # Key A
                me.send_rc_control(0, 0, 0, speed)
                log("Turn clockwise")
                direction = "TURN CLOCKWISE"
                messages.append(direction)
                last_manual_command = k
            elif k == ord('d'):
                # Key D
                me.send_rc_control(0, 0, 0, -speed)
                log("Turn counterclockwise")
                direction = "TURN COUNTERCLOCKWISE"
                messages.append(direction)
                last_manual_command = k
        else:
            log(str(k))

out.release()
out_processed.release()
out_log.close()
cv2.destroyAllWindows()
