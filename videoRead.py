import frameProcessing as fp
import functions as f
import time
import cv2

global_pid = [0.4, 0.4, 0]
global_previous_error = [0, 0, 0]

messages = []
pause = False
fps = 30
# cap = cv2.VideoCapture("Resources/tello_video_test.mp4")
cap = cv2.VideoCapture("Resources/output.avi")

while cap.isOpened():
    if not pause:
        ret, img = cap.read()

    messages.clear()

    # 30 fps
    if fps > 0:
        time.sleep(1 / fps)
        text = str(fps) + " fps"
        if pause:
            text += " (Paused)"
        messages.append(text)

    if not ret:
        print("Error reading file...")
        break

    # print(img.shape)

    # Processing frame
    result, img = fp.read(img, m=messages, size=(1024, 768))

    # print(img.shape)

    # Drone movement
    # print(result)
    result = f.roll_throttle_pitch(result[0], result[1], result[2], global_pid, global_previous_error)
    global_previous_error = result[3]
    # print(result)

    k = cv2.waitKeyEx(1)

    if k == -1:
        continue
    elif k == 32:
        # Pause and continue
        pause = not pause
    elif k == ord('q') or k == 27:
        # Quit
        break
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
