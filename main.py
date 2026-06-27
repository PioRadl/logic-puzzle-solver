import pandas as pd
import argparse
from ocr_from_img import get_board_from_image
from dominosa_solver import solve, display_with_marked_pairs, check_solution

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("filename", help="The file with the board, either a csv or an image (png/jpg)")
    parser.add_argument("--logs", action="store_true", help="Whether you want logs from the solution process")
    args = parser.parse_args()

    filename = args.filename
    if str.endswith(filename, ".csv"):
        board = pd.read_csv("csvs/image_actual.csv", header=None).to_numpy().tolist()
    elif str.endswith(filename, ".png") or str.endswith(filename, ".jpg"):
        board = get_board_from_image(filename)

    print("Board to solve:")
    for row in board:
        print(*row)
    pairs = solve(board, log = args.logs)
    print("Solution:")
    display_with_marked_pairs(board, pairs)

    if check_solution(board, pairs):
        print("The puzzle solved was solved correctly")

if __name__ == "__main__":
    main()