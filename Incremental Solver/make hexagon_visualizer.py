import json


# This script generates an HTML file to visualize the hexagonal grid and its connections.
# This version contains a completely new, robust grid generation algorithm based on
# axial coordinates, which is the standard, correct way to solve this problem.
# It also includes an enhanced automated test report for immediate verification.

# --- Core Hexagon Logic (Rewritten for correctness) ---

def generate_hexagon_board_details(radius):
    """
    Generates all board data using a robust axial coordinate system.
    This is the definitive fix for the neighbor logic.
    """
    print("Generating hexagon data using robust axial coordinate method...")

    # 1. Generate a set of all valid axial coordinates for the given radius
    axial_coords = set()
    for q in range(-radius, radius + 1):
        for r in range(-radius, radius + 1):
            if abs(q) + abs(r) + abs(-q - r) <= radius * 2:
                axial_coords.add((q, r))

    # 2. Convert axial coordinates to an "even-q" offset system for rendering
    def axial_to_offset(q, r):
        col = q
        row = r + (q - (q & 1)) // 2
        return (row, col)

    offset_coords_unnormalized = {axial_to_offset(q, r) for q, r in axial_coords}

    # 3. Normalize the offset coordinates to start from (0,0) for easier use
    if not offset_coords_unnormalized:
        return {}, {}, 0

    min_r = min(cell[0] for cell in offset_coords_unnormalized)
    min_c = min(cell[1] for cell in offset_coords_unnormalized)
    valid_cells = {(r - min_r, c - min_c) for r, c in offset_coords_unnormalized}

    # 4. Create mappings between all three coordinate systems for lookups
    offset_to_axial_map = {}
    axial_to_offset_map = {}
    for q, r in axial_coords:
        norm_offset = (axial_to_offset(q, r)[0] - min_r, axial_to_offset(q, r)[1] - min_c)
        offset_to_axial_map[norm_offset] = (q, r)
        axial_to_offset_map[(q, r)] = norm_offset

    # 5. Build the adjacency map using the simple and foolproof axial system
    axial_directions = [(+1, 0), (+1, -1), (0, -1), (-1, 0), (-1, +1), (0, +1)]
    adjacency_map_by_coord = {cell: [cell] for cell in valid_cells}
    for cell_offset in valid_cells:
        start_axial = offset_to_axial_map[cell_offset]
        for dq, dr in axial_directions:
            neighbor_axial = (start_axial[0] + dq, start_axial[1] + dr)
            if neighbor_axial in axial_to_offset_map:
                neighbor_offset = axial_to_offset_map[neighbor_axial]
                adjacency_map_by_coord[cell_offset].append(neighbor_offset)

    # 6. Create index-based mappings for the solver/frontend
    sorted_coords = sorted(list(valid_cells), key=lambda item: (item[1], item[0]))
    coord_to_index = {coord: i for i, coord in enumerate(sorted_coords)}
    adj_map_indices = {
        coord_to_index[coord]: sorted([coord_to_index[n] for n in neighbors])
        for coord, neighbors in adjacency_map_by_coord.items()
    }

    # 7. Create rendering map for the visualizer
    render_map = {}
    unique_cols = sorted(list(set(c for r, c in sorted_coords)))
    col_to_c_idx = {c_val: i for i, c_val in enumerate(unique_cols)}
    rows_in_col = {c: sorted([r_val for r_val, c_val in sorted_coords if c_val == c]) for c in unique_cols}
    for r, c in sorted_coords:
        index = coord_to_index[(r, c)]
        c_idx = col_to_c_idx[c]
        r_idx = rows_in_col[c].index(r)
        render_map[index] = (c_idx, r_idx)

    return adj_map_indices, render_map, len(unique_cols)


# --- HTML Generation ---

def create_visualizer_html(adj_map, render_map, num_cols):
    """Generates the full HTML content with an enhanced auto-tester."""
    adj_map_json = json.dumps(adj_map)

    javascript_code = f"""
        const ADJACENCY_MAP = {adj_map_json};
        const RENDER_MAP = {json.dumps(render_map)};
        const NUM_COLS = {num_cols};
        const NUM_TILES = Object.keys(RENDER_MAP).length;

        // --- Board Rendering ---
        const boardContainer = document.getElementById('board-container');
        const columns = Array.from({{ length: NUM_COLS }}, () => {{
            const colDiv = document.createElement('div');
            colDiv.className = 'column';
            boardContainer.appendChild(colDiv);
            return colDiv;
        }});
        const tiles = {{}};
        for (let i = 0; i < NUM_TILES; i++) {{
            const tile = document.createElement('div');
            tile.className = 'tile';
            tile.textContent = i;
            tile.dataset.index = i;
            tiles[i] = tile;
            const [col_idx, row_idx] = RENDER_MAP[i];
            columns[col_idx].appendChild(tile);
            tile.addEventListener('click', () => handleTileClick(i));
        }}
        function handleTileClick(clickedIndex) {{
            Object.values(tiles).forEach(t => t.classList.remove('selected', 'affected'));
            const affectedTiles = ADJACENCY_MAP[clickedIndex];
            if (!affectedTiles) return;
            affectedTiles.forEach(index => {{
                const tileElement = tiles[index];
                if (tileElement) {{
                    tileElement.classList.add(index == clickedIndex ? 'selected' : 'affected');
                }}
            }});
        }}

        // --- Automated Testing ---
        document.addEventListener('DOMContentLoaded', () => {{
            const testCases = {{
                18: {{ expected: [11, 12, 17, 18, 19, 24, 25] }},
                32: {{ expected: [26, 27, 31, 32, 36] }},
                21: {{ expected: [14, 20, 21, 27] }}
            }};

            const reportElement = document.getElementById('test-report');
            let fullReport = '';

            for (const tileIndexStr in testCases) {{
                const testCase = testCases[tileIndexStr];
                const expected = testCase.expected;
                const tileIndex = parseInt(tileIndexStr, 10);
                const actual = ADJACENCY_MAP[tileIndex] || [];

                expected.sort((a,b)=>a-b);
                actual.sort((a,b)=>a-b);

                const missing = expected.filter(id => !actual.includes(id));
                const extra = actual.filter(id => !expected.includes(id));
                const isPass = missing.length === 0 && extra.length === 0;

                fullReport += '<div class="test-case">';
                fullReport += `<h3>TESTING TILE ${{tileIndex}}: ` + (isPass ? '<span class=pass>PASS</span>' : '<span class=fail>FAIL</span>') + '</h3>';
                fullReport += '<div class="comparison-grid">';

                // Create mini-visualization for expected and actual
                fullReport += '<div><h4>Expected</h4>' + createMiniGrid(tileIndex, expected) + '</div>';
                fullReport += '<div><h4>Actual</h4>' + createMiniGrid(tileIndex, actual) + '</div>';

                fullReport += '</div>'; // end comparison-grid

                if (!isPass) {{
                    fullReport += '<div class="details">';
                    fullReport += `  EXPECTED: ${{JSON.stringify(expected)}}\\n`;
                    fullReport += `  ACTUAL  : ${{JSON.stringify(actual)}}\\n`;
                    if(missing.length > 0) {{ fullReport += `  <span class=fail>MISSING : ${{JSON.stringify(missing)}}</span>\\n`; }}
                    if(extra.length > 0)   {{ fullReport += `  <span class=fail>EXTRA   : ${{JSON.stringify(extra)}}</span>\\n`; }}
                    fullReport += '</div>';
                }}
                fullReport += '</div>'; // end test-case
            }}
            reportElement.innerHTML = fullReport;

            handleTileClick(Object.keys(testCases)[0]);
        }});

        function createMiniGrid(centerIndex, affectedIndices) {{
            let gridHtml = '<div class="mini-grid">';
            const size = 5; // 5x5 grid around the center
            const centerOffset = Math.floor(size/2);

            // Find center tile's render position to anchor the mini-grid
            const [centerCol, centerRow] = RENDER_MAP[centerIndex] || [0,0];

            for (let r_offset = -centerOffset; r_offset <= centerOffset; r_offset++) {{
                for (let c_offset = -centerOffset; c_offset <= centerOffset; c_offset++) {{
                    const targetCol = centerCol + c_offset;
                    const targetRow = centerRow + r_offset;

                    // Find if a tile exists at this render position
                    let tileIndex = -1;
                    for (const [idx, pos] of Object.entries(RENDER_MAP)) {{
                        if (pos[0] === targetCol && pos[1] === targetRow) {{
                            tileIndex = parseInt(idx, 10);
                            break;
                        }}
                    }}

                    if (tileIndex !== -1) {{
                        let className = 'mini-tile';
                        if (affectedIndices.includes(tileIndex)) {{
                            className += (tileIndex === centerIndex) ? ' selected' : ' affected';
                        }}
                        gridHtml += `<div class="${{className}}"></div>`;
                    }} else {{
                        gridHtml += '<div class="mini-tile empty"></div>';
                    }}
                }}
            }}
            gridHtml += '</div>';
            return gridHtml;
        }}

    """

    html_template = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Hexagon Grid Visualizer (Final Corrected Version)</title>
    <style>
        body {{
            font-family: monospace; display: flex; flex-direction: column;
            align-items: center; background-color: #1a202c; color: #e2e8f0; margin: 2rem;
        }}
        #main-container {{ display: flex; flex-direction: column; align-items: center; gap: 2rem; }}
        #board-container {{ display: flex; justify-content: center; align-items: center; gap: 8px; }}
        .column {{ display: flex; flex-direction: column; gap: 8px; }}
        .tile {{
            width: 40px; height: 40px; font-size: 1rem;
            background-color: #4a5568; border: 2px solid #718096; border-radius: 50%;
            display: flex; align-items: center; justify-content: center; font-weight: bold;
            cursor: pointer; transition: all 0.2s ease-in-out; user-select: none;
        }}
        .tile:hover {{ border-color: #a0aec0; transform: scale(1.05); }}
        .selected {{ background-color: #4299e1; border-color: #90cdf4; color: #fff; }}
        .affected {{ background-color: #f56565; border-color: #feb2b2; color: #fff; }}

        #test-report-container {{
            width: 100%; max-width: 800px; background-color: #2d3748;
            border: 1px solid #4a5568; border-radius: 8px; padding: 1rem;
        }}
        .test-case {{ border-bottom: 1px solid #4a5568; padding-bottom: 1rem; margin-bottom: 1rem; }}
        .test-case:last-child {{ border-bottom: none; margin-bottom: 0; }}
        .details {{ white-space: pre-wrap; word-wrap: break-word; margin-top: 0.5rem; font-size: 0.85rem; }}
        .pass {{ color: #68d391; font-weight: bold; }}
        .fail {{ color: #fc8181; font-weight: bold; }}

        .comparison-grid {{ display: flex; justify-content: space-around; gap: 2rem; margin-top: 1rem; }}
        .mini-grid {{
            display: grid; grid-template-columns: repeat(5, 1fr);
            gap: 2px; width: 120px; height: 120px;
        }}
        .mini-tile {{
            width: 100%; height: 100%; border-radius: 50%; background-color: #4a5568;
        }}
        .mini-tile.empty {{ background-color: transparent; }}
    </style>
</head>
<body>
    <div id="main-container">
        <h1>Hexagon Grid Visualizer</h1>
        <div id="board-container"></div>
        <div id="test-report-container">
            <h2>Automated Test Results</h2>
            <div id="test-report"></div>
        </div>
    </div>
    <script>
        {javascript_code}
    </script>
</body>
</html>
"""
    return html_template


def main():
    """Main function to generate the HTML file."""
    radius = 3
    adj_map, render_map, num_cols = generate_hexagon_board_details(radius)

    print("Creating HTML content with enhanced automated tests...")
    html_content = create_visualizer_html(adj_map, render_map, num_cols)

    filename = "hexagon_visualizer.html"
    with open(filename, "w", encoding="utf-8") as f:
        f.write(html_content)

    print(f"\\nSuccess! '{filename}' has been created.")
    print("Open it in your browser to see the final test results.")


if __name__ == "__main__":
    main()

