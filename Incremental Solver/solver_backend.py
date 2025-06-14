from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import numpy as np
import math
from functools import lru_cache


# --- Data Models for API ---
class Puzzle(BaseModel):
    board: list | list[list[int]]
    difficulty: str


# --- FastAPI App Initialization ---
app = FastAPI()
origins = ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- CORRECTED AND VERIFIED HEXAGON LOGIC ---
@lru_cache(maxsize=None)
def get_hexagon_board_details(radius=3):
    """
    Generates and caches all necessary data structures for the hexagonal board
    using the standard, correct hexagon generation formula.
    """
    print(f"[Solver] Pre-calculating hexagonal grid details using standard algorithm...")

    axial_coords = set()
    for q in range(-radius, radius + 1):
        r1 = max(-radius, -q - radius)
        r2 = min(radius, -q + radius)
        for r in range(r1, r2 + 1):
            axial_coords.add((q, r))

    def axial_to_offset(q, r):
        col, row = q, r + (q - (q & 1)) // 2
        return (row, col)

    offset_coords_unnormalized = {axial_to_offset(q, r) for q, r in axial_coords}
    if not offset_coords_unnormalized: return {}

    min_r, min_c = min(c[0] for c in offset_coords_unnormalized), min(c[1] for c in offset_coords_unnormalized)
    valid_cells = {(r - min_r, c - min_c) for r, c in offset_coords_unnormalized}

    offset_to_axial_map, axial_to_offset_map = {}, {}
    for q, r in axial_coords:
        norm_offset = (axial_to_offset(q, r)[0] - min_r, axial_to_offset(q, r)[1] - min_c)
        offset_to_axial_map[norm_offset], axial_to_offset_map[(q, r)] = (q, r), norm_offset

    axial_directions = [(+1, 0), (+1, -1), (0, -1), (-1, 0), (-1, +1), (0, +1)]
    adjacency_map_by_coord = {cell: [cell] for cell in valid_cells}
    for cell_offset in valid_cells:
        start_axial = offset_to_axial_map[cell_offset]
        for dq, dr in axial_directions:
            neighbor_axial = (start_axial[0] + dq, start_axial[1] + dr)
            if neighbor_axial in axial_to_offset_map:
                adjacency_map_by_coord[cell_offset].append(axial_to_offset_map[neighbor_axial])

    sorted_coords = sorted(list(valid_cells), key=lambda item: (item[1], item[0]))
    coord_to_index = {coord: i for i, coord in enumerate(sorted_coords)}
    adj_map_indices = {
        coord_to_index[coord]: sorted([coord_to_index[n] for n in neighbors])
        for coord, neighbors in adjacency_map_by_coord.items()
    }

    return adj_map_indices


# --- Self-Verification Test (RESTORED) ---
def run_backend_tests():
    """
    Runs a one-time check when the server starts to verify the hexagon logic.
    Prints a simple PASS/FAIL report to the console.
    """
    print("\n--- Running Backend Hexagon Logic Verification ---")
    adj_map = get_hexagon_board_details()

    # These are the ground-truth test cases with the corrected list for tile 32.
    test_cases = {
        18: [11, 12, 17, 18, 19, 24, 25],
        32: [26, 27, 31, 32, 36],
        21: [14, 20, 21, 27]
    }
    all_passed = True

    for tile, expected_neighbors in test_cases.items():
        actual_neighbors = adj_map.get(tile, [])
        expected_neighbors.sort()

        if actual_neighbors == expected_neighbors:
            print(f"  [PASS] Tile {tile}")
        else:
            all_passed = False
            print(f"  [FAIL] Tile {tile}")
            print(f"    - Expected: {expected_neighbors}")
            print(f"    - Actual:   {actual_neighbors}")

    # print("-" * 50)
    # if all_passed:
    #     print("--- Verification PASSED. The hexagon logic is correct. ---")
    # else:
    #     print("--- Verification FAILED. The logic is incorrect ---")
    print("-" * 50 + "\n")


# Run the verification when the application starts
run_backend_tests()


# --- Gaussian Elimination Solver ---
def gaussian_elimination_mod(A, b, m):
    """Solves Ax = b (mod m) using Gaussian elimination."""
    n = A.shape[0]
    Ab = np.hstack([A.copy().astype(np.int64), b.copy().reshape(-1, 1).astype(np.int64)])
    print(f"[Solver] Performing Gaussian elimination modulo {m}...")

    for i in range(n):
        pivot_row = i
        while pivot_row < n and Ab[pivot_row, i] == 0: pivot_row += 1
        if pivot_row == n: continue
        Ab[[i, pivot_row]] = Ab[[pivot_row, i]]
        try:
            inv = pow(int(Ab[i, i]), -1, m)
        except ValueError:
            return None
        Ab[i] = (Ab[i] * inv) % m
        for j in range(n):
            if i != j: Ab[j] = (Ab[j] - Ab[j, i] * Ab[i]) % m
    if np.any(np.all(Ab[:, :-1] == 0, axis=1) & (Ab[:, -1] != 0)): return None

    x = np.zeros(n, dtype=int)
    for i in range(n - 1, -1, -1):
        if Ab[i, i] == 1:
            val = Ab[i, -1] - np.dot(Ab[i, i + 1:-1], x[i + 1:])
            x[i] = val % m
        else:
            x[i] = 0
    return x


# --- Main Solver Function ---
def solve(initial_board, difficulty):
    # Determine grid properties from difficulty
    if difficulty == 'easy':
        size_rc, modulus, layout = 3, 4, 'grid'
        n = size_rc * size_rc
    elif difficulty == 'medium':
        size_rc, modulus, layout = 4, 4, 'grid'
        n = size_rc * size_rc
    elif difficulty == 'hard' or difficulty == 'expert':
        n, modulus, layout = 37, (2 if difficulty == 'hard' else 6), 'hexagon'
    else:
        return None

    print(f"\n[Solver] Using Linear Algebra for '{difficulty}' mode (mod {modulus}, {n} tiles)...")

    # Build the effects matrix 'A'
    A = np.zeros((n, n), dtype=int)
    if layout == 'grid':
        adj_map = {
            k: [i for i in range(n) if abs(i // size_rc - k // size_rc) <= 1 and abs(i % size_rc - k % size_rc) <= 1]
            for k in range(n)}
    else:
        adj_map = get_hexagon_board_details()

    for button_idx, affected_list in adj_map.items():
        for tile_idx in affected_list:
            A[tile_idx, button_idx] = 1

    # Create the target state vector 'b'
    initial_flat = np.array(initial_board).flatten()
    b = (1 - initial_flat) % modulus

    # Solve the system Ax = b for the number of presses 'x'
    if difficulty == 'expert':
        x_mod2 = gaussian_elimination_mod(A, b % 2, 2)
        x_mod3 = gaussian_elimination_mod(A, b % 3, 3)
        if x_mod2 is None or x_mod3 is None: return None
        x = np.zeros(n, dtype=int)
        for i in range(n):
            for k in range(6):
                if k % 2 == x_mod2[i] and k % 3 == x_mod3[i]:
                    x[i] = k;
                    break
    else:
        x = gaussian_elimination_mod(A, b, modulus)

    if x is None: return None

    # --- Build detailed solution steps for the frontend ---
    solution_steps = []
    current_board = list(initial_flat)

    click_path = []
    if layout == 'grid':
        for i, count in enumerate(x):
            if count > 0: click_path.extend([[i // size_rc, i % size_rc]] * count)
    else:
        for i, count in enumerate(x):
            if count > 0: click_path.extend([i] * count)

    for click in click_path:
        click_index = click if layout == 'hexagon' else click[0] * size_rc + click[1]
        affected_tiles = adj_map.get(click_index, [])

        # Apply the click to the current board state
        for tile_idx in affected_tiles:
            current_board[tile_idx] = ((current_board[tile_idx] - 1 + 1) % modulus) + 1

        # --- THIS IS THE FIX ---
        # The 'current_board' contains numpy.int64 types which are not JSON serializable.
        # We must convert them to standard Python integers before appending.
        solution_steps.append({
            "click": click,
            "affected_tiles": affected_tiles,
            "board_state": [int(i) for i in current_board]  # Convert numpy types to python ints
        })

    print(f"[Solver] Calculation complete. Solution found in {len(solution_steps)} steps.")
    return solution_steps


# --- API Endpoint ---
@app.post("/solve")
async def solve_puzzle(puzzle: Puzzle):
    # The key is now "solution_steps" to match the frontend
    solution = solve(puzzle.board, puzzle.difficulty)
    return {"solution_steps": solution}
