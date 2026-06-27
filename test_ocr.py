import os
import pandas as pd
from ocr_from_img import get_board_from_image
import cv2

def visualize_bbox(image_path, bbox, padding=3):
    x, y, w, h = bbox
    img = cv2.imread(image_path)
    img_h, img_w = img.shape[:2]

    x1 = max(0, x - padding)
    y1 = max(0, y - padding)
    x2 = min(img_w, x + w + padding)
    y2 = min(img_h, y + h + padding)

    fragment = img[y1:y2,x1:x2]
    fragment = cv2.resize(fragment, dsize=None, fx=4, fy=4)
    cv2.imshow("Cut fragment of the image", fragment)
    cv2.waitKey(0)


def test(image_path, csv_path, log=False, visualize=False):
    # try:
        actual = pd.read_csv(csv_path, header=None).to_numpy().tolist()
        predicted, bboxes = get_board_from_image(image_path, return_bboxes=True, log=visualize)

        errors = []
        for i, (row_act, row_pre) in enumerate(zip(actual, predicted)):
            for j, (cell_act, cell_pre) in enumerate(zip(row_act, row_pre)):
                if cell_act != cell_pre:
                    errors.append((i, j))
        
        if errors:
            if log:
                print(f"Encountered {len(errors)} discrepancies")
                for err in errors:
                    print(f"Inconsistency at the position {err}. Predicted {predicted[err[0]][err[1]]}, should be {actual[err[0]][err[1]]}")
                    if visualize:
                        visualize_bbox(image_path, bboxes[err[0]*len(predicted[0]) + err[1]])
            return False
        else:
            return True
    # except Exception as e:
    #     print("Test unsuccessful, encountered following error:")
    #     print(e)
    #     return False
    

def test_all():
    images = os.listdir("images")
    for image in images:
        csv_path = os.path.join("csvs", image[:-3] + "csv")
        if test(os.path.join("images", image), csv_path, log=True):
            print(f"Test for image {image} was successful")
        else:
            print(f"Test for image {image} was unsuccessful")

if __name__ == "__main__":
    test_all()