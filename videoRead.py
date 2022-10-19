import frameProcessing as fp
import functions as f
import time
import cv2
from datetime import datetime
from datetime import timedelta

global_previous_error = [0, 0, 0]

messages = []
pause = False

size = (1024, 768)

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

fps = 30
# cap = cv2.VideoCapture("Resources/tello_video_test.mp4")
# cap = cv2.VideoCapture("Resources/output.avi")

# cap = cv2.VideoCapture("Video/20221015214059_output_TARGET.avi")

cap = cv2.VideoCapture("Video/20221015224958_output_CRASH.avi")

gray_scale = False

def land():
    log("Land")
    messages.append("Land")


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
    n = datetime.now()
    text = n.strftime("%d/%m/%Y, %H:%M:%S:%f") + " " + str(m)
    print(text)


while cap.isOpened():
    if not pause:
        ret, img = cap.read()
        if gray_scale:
            img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # 30 fps
    if fps > 0:
        time.sleep(1 / fps)
        message = str(fps) + " fps"
        if pause:
            message += " (Paused)"
        messages.append(message)

    if not ret:
        print("Error reading file...")
        break

    # print(img.shape)

    # Processing frame
    result, movements_from_image, img_resized = fp.read(img, m=messages, size=(1024, 768))
    messages.clear()
    messages.append("Time on Target: " + str(timedelta(seconds=secs_on_target)))
    messages.append("Time Elapsed: " + str(timedelta(seconds=int(time.time() - time_started))))

    # print(img.shape)

    # Drone movement only if return success
    if result == "SUCCESS":
        # ToDo: Try to consider a tolerance
        time_on_target = 0
        secs_on_target = 0
        # log(result)
        # result = f.roll_throttle_pitch_v2(movements_from_image[0], movements_from_image[1], movements_from_image[2],
        #                                   global_previous_error)
        result = f.roll_throttle_pitch(movements_from_image[0], movements_from_image[1], movements_from_image[2],
                                       global_previous_error)
        # ToDo: Include YAW in parameters
        global_previous_error = result[3]

        # log(result)
        # ToDo: What happen if value is 0 0 0 0 ?
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
        log("SEND_RC_CONTROL: [" + str(result[0]) + ", " + str(-result[2]) + "," + str(-result[1]) + "," + str(
            0) + "]")
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

    k = cv2.waitKeyEx(1)

    if k == -1:
        continue
    elif k == 32:
        # Pause and continue
        pause = not pause
    elif k == ord('q') or k == 27:
        # Quit
        break
    elif k == ord('g'):
        gray_scale = not gray_scale
    elif k == ord('0'):
        fps = 30
    elif k == ord('1'):
        fps = 1
    elif k == ord('9'):
        fps = 300
    elif k == 45:
        # Decrease fps
        if fps > 10:
            fps -= 10
        elif fps > 1:
            fps -= 1
    elif k == 43:
        # Increase fps
        if fps < 10:
            fps += 1
        else:
            fps += 10
    else:
        print(k)

cap.release()
cv2.destroyAllWindows()
