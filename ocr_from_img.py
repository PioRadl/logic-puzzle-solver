import cv2
import numpy as np
import easyocr
from shapely import box
from sklearn.cluster import DBSCAN
import pandas as pd

# pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'  # Adjust path if necessary

def get_bboxes(image_path, log = False):
    img = cv2.imread(image_path)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (7, 3))
    dilated = cv2.dilate(thresh, kernel, iterations=1)

    contours, _ = cv2.findContours(dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    count = 0
    bboxes = []
    for contour in contours:
        x, y, w, h = cv2.boundingRect(contour)
        
        # Very loose filter: Just ignore tiny specs of dust (less than 5x10 pixels)
        cv2.rectangle(img, (x, y), (x + w, y + h), (0, 255, 0), 2)
        count += 1
        bboxes.append((x, y, w, h))

    if log:
        print(f"Total valid shapes found: {count}")

        cv2.imshow('Step 1: Black and White', thresh)
        cv2.imshow('Step 2: Dilated (Glued together)', dilated)
        cv2.imshow('Step 3: Final Boxes', img)

        cv2.waitKey(0)
        cv2.destroyAllWindows()
    return bboxes


def read_cells_batched(img, boxes, reader, padding=3, batch_size=32, max_possible_len = 2):
    img_h, img_w = img.shape[:2]
    easyocr_boxes = []
    
    for box in boxes:
        x, y, w, h = box
        
        x1 = max(0, x - padding)
        y1 = max(0, y - padding)
        x2 = min(img_w, x + w + padding)
        y2 = min(img_h, y + h + padding)
        
        easyocr_boxes.append([x1, x2, y1, y2])
        
    if not easyocr_boxes:
        return []

    results = reader.recognize(
        img, 
        horizontal_list=easyocr_boxes, 
        allowlist='0123456789',
        batch_size=batch_size,
        detail=0,
        free_list=[]
    )
    
    cleaned_results = [text.strip()[-2:] for text in results]
    
    return cleaned_results


def sort_dbscan_labels(coords, labels):
    unique_labels = set(labels) - {-1}
    
    centroids = {lbl: np.mean(coords[labels == lbl]) for lbl in unique_labels}
    
    sorted_old_labels = sorted(unique_labels, key=lambda l: centroids[l])
    
    remap = {old: new for new, old in enumerate(sorted_old_labels)}
    remap[-1] = -1 # Ensure noise stays as -1
    
    return np.array([remap[lbl] for lbl in labels])


def get_board_from_image(image_path, log = False, return_bboxes = False):
    reader = easyocr.Reader(['en'])
    bboxes = get_bboxes(image_path, log)
    print(f"Found {len(bboxes)} boxes")
    centers = [(x + w // 2, y + h // 2) for (x, y, w, h) in bboxes]
    x_centers = np.array(centers)[:, 0]
    y_centers = np.array(centers)[:, 1]

    columns = DBSCAN(eps=5, min_samples=5).fit(x_centers.reshape(-1, 1))
    col_labels = columns.labels_

    rows = DBSCAN(eps=5, min_samples=5).fit(y_centers.reshape(-1, 1))
    row_labels = rows.labels_

    col_labels = sort_dbscan_labels(x_centers, col_labels)
    row_labels = sort_dbscan_labels(y_centers, row_labels)

    to_delete = []
    for i, (bbox, col_label, row_label) in enumerate(zip(bboxes, col_labels, row_labels)):
        # print(f"Box: {bbox}, Column: {col_label}, Row: {row_label}")
        if col_label == -1 or row_label == -1:
            to_delete.append(i)

    bboxes = [box for i, box in enumerate(bboxes) if i not in to_delete]
    col_labels = [label for i, label in enumerate(col_labels) if i not in to_delete]
    row_labels = [label for i, label in enumerate(row_labels) if i not in to_delete]

    combined = list(zip(row_labels, col_labels, bboxes))
    combined.sort(key=lambda item: (item[0], item[1]))
    row_labels, col_labels, bboxes = zip(*combined)

    results = read_cells_batched(cv2.imread(image_path), bboxes, reader)
    results = [int(x) for x in results]

    n_cols = len(np.unique(columns.labels_[columns.labels_ != -1]))
    n_rows = len(np.unique(rows.labels_[rows.labels_ != -1]))

    results = np.array(results).reshape((n_rows, n_cols)).tolist()
    if return_bboxes:
        return results, bboxes
    return results
    


if __name__ == "__main__":
    image_path = "image.png"
    reader = easyocr.Reader(['en'])
    bboxes = get_bboxes(image_path)

    centers = [(x + w // 2, y + h // 2) for (x, y, w, h) in bboxes]
    # img = cv2.imread(image_path)
    # for center in centers:
    #     cv2.circle(img, center, 3, (0, 0, 255), -1)
    # cv2.imshow('Detected Centers', img)
    # cv2.waitKey(0)

    x_centers = np.array(centers)[:, 0]
    y_centers = np.array(centers)[:, 1]

    columns = DBSCAN(eps=5, min_samples=5).fit(x_centers.reshape(-1, 1))
    col_labels = columns.labels_

    rows = DBSCAN(eps=5, min_samples=5).fit(y_centers.reshape(-1, 1))
    row_labels = rows.labels_

    col_labels = sort_dbscan_labels(x_centers, col_labels)
    row_labels = sort_dbscan_labels(y_centers, row_labels)

    to_delete = []
    for i, (bbox, col_label, row_label) in enumerate(zip(bboxes, col_labels, row_labels)):
        # print(f"Box: {bbox}, Column: {col_label}, Row: {row_label}")
        if col_label == -1 or row_label == -1:
            to_delete.append(i)

    bboxes = [box for i, box in enumerate(bboxes) if i not in to_delete]
    col_labels = [label for i, label in enumerate(col_labels) if i not in to_delete]
    row_labels = [label for i, label in enumerate(row_labels) if i not in to_delete]

    combined = list(zip(row_labels, col_labels, bboxes))
    combined.sort(key=lambda item: (item[0], item[1]))
    row_labels, col_labels, bboxes = zip(*combined)

    actual = pd.read_csv("image_actual.csv", header=None)
    print(actual)
    print(np.array(actual).tolist())

    # Read OCR for each detected bounding box

    results = read_cells_batched(cv2.imread(image_path), bboxes, reader)
    print(len(results))
    errors = 0
    for i, (predicted, bbox, col_label, row_label) in enumerate(zip(results, bboxes, col_labels, row_labels)):
        # print(i, predicted, bbox, col_label, row_label, actual.iloc[row_label, col_label])
        if predicted != str(actual.iloc[row_label, col_label]):
            print(f"Should be {str(actual.iloc[row_label, col_label])} but detected {predicted}")
            errors += 1
    print("Errors encountered:", errors)



