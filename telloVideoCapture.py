from djitellopy import tello
import frameProcessing as fp
import functions as f
import time
import cv2
from datetime import datetime

global_pid = [0.4, 0.4, 0]
global_previous_error = [0, 0, 0]
size = (1024, 768)

messages = []
pause = False
autonomous = False

me = tello.Tello()
me.connect()
print("Battery Level: ", me.get_battery(), "%")
me.streamon()

now = datetime.now()
prefix = now.strftime("%Y%m%d%H%M%S")

fourcc = cv2.VideoWriter_fourcc(*'XVID')
out = cv2.VideoWriter(prefix + " output.avi", fourcc, 30.0, size)
out_processed = cv2.VideoWriter(prefix + " output_processed.avi", fourcc, 30.0, size)

while True:
    if not pause:
        img = me.get_frame_read().frame
        img_resize = cv2.resize(img, size)

    # Recording original video resized
    out.write(img_resize)

    # time.sleep(1 / 10)

    # Processing frame
    result, img_resize = fp.read(img_resize, me, m=messages)
    messages.clear()

    # Recording video processed
    out_processed.write(img_resize)

    # Drone movement
    # print(result)
    result = f.roll_throttle_pitch(result[0], result[1], result[2], global_pid, global_previous_error)
    # ToDo: Include YAW in parameters
    global_previous_error = result[3]

    if autonomous:
        print(result)
        me.send_rc_control(result[0], result[1], result[2], 0)
        message = ""
        # Roll
        if result[0] > 0:
            message += " RIGHT: " + str(result[0])
        elif result[0] < 0:
            message += " LEFT: " + str(result[0])
        else:
            message += " HOVER "
        # Pitch
        if result[1] > 0:
            message += " FORWARD: " + str(result[1])
        elif result[1] < 0:
            message += " BACKWARD: " + str(result[1])
        else:
            message += " HOVER "
        # Throttle
        if result[2] > 0:
            message += " UP: " + str(result[2])
        elif result[2] < 0:
            message += " DOWN: " + str(result[2])
        else:
            message += " HOVER "
        messages.append("MODE: AUTONOMOUS " + message)
    else:
        messages.append("MODE: MANUAL")

    # time.sleep(1 / 10)

    k = cv2.waitKeyEx(1)

    # me.send_rc_control
    # left_right_velocity - forward_backward_velocity - up_down_velocity - yaw_velocity

    if k == -1:
        continue
    elif k == 32:
        # Pause and continue
        print("Pause")
        messages.append("Pause")
        pause = not pause
    elif k == ord('y'):
        # Autonomous
        print("Autonomous ON")
        messages.append("Autonomous ON")
        autonomous = True
    elif k == ord('x'):
        # Autonomous
        print("Autonomous OFF")
        messages.append("Autonomous OFF")
        autonomous = False
    elif k == ord('q') or k == 27:
        # Quit
        print("Stream off")
        messages.append("Stream OFF")
        autonomous = False
        me.streamoff()
        print("Land")
        messages.append("Land")
        # me.land()
        break
    elif k == 2359296:
        # Home (Inicio)
        print("Take off")
        messages.append("Take off")
        me.takeoff()
    elif k == 2490368:
        # Up Arrow
        me.send_rc_control(0, 20, 0, 0)
        print("Forward")
        messages.append("MANUAL: FORWARD")
    elif k == 2621440:
        # Down Arrow
        me.send_rc_control(0, -20, 0, 0)
        print("Backward")
        messages.append("MANUAL: BACKWARD")
    elif k == 2424832:
        # Left Arrow
        me.send_rc_control(-20, 0, 0, 0)
        print("Left")
        messages.append("MANUAL: LEFT")
    elif k == 2555904:
        # Right Arrow
        me.send_rc_control(20, 0, 0, 0)
        print("Right")
        messages.append("MANUAL: RIGHT")
    elif k == ord('w'):
        # Key K
        me.send_rc_control(0, 0, 20, 0)
        print("Up")
        messages.append("MANUAL: UP")
    elif k == ord('s'):
        # Key S
        me.send_rc_control(0, 0, -20, 0)
        print("Down")
        messages.append("MANUAL: DOWN")
    elif k == ord('a'):
        # Key A
        me.send_rc_control(0, 0, 0, 20)
        print("Turn clockwise")
        messages.append("MANUAL: TURN CLOCKWISE")
    elif k == ord('d'):
        # Key D
        me.send_rc_control(0, 0, 0, -20)
        print("Turn counterclockwise")
        messages.append("MANUAL: TURN COUNTERCLOCKWISE")
    elif k == ord('0'):
        # Keypad 0
        me.send_rc_control(0, 0, 0, 0)
        print("Stop")
        messages.append("HOVER")
    else:
        print(k)

out.release()
cv2.destroyAllWindows()
