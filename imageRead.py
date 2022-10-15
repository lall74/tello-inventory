import frameProcessing as fp
import cv2

img = cv2.imread("Resources/tello_photo_200.png")
fp.read(img)

while True:
    if cv2.waitKey(1) & 0xFF == ord('1'):
        img = cv2.imread("Resources/tello_photo_200.png")
        fp.read(img)
        print('1')
    elif cv2.waitKey(1) & 0xFF == ord('2'):
        img = cv2.imread("Resources/tello_photo_150.png")
        fp.read(img)
        print('2')

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cv2.destroyAllWindows()

