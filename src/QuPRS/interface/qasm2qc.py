import re
import sys
from pathlib import Path

def convert_qasm_to_qc(oldfile, output_dir=None):
    # Determine the output directory
    if output_dir:
        output_dir = Path(output_dir)
    else:
        output_dir = Path(oldfile).parent

    # Define the new file name in the specified or default directory
    newfile = output_dir / f"{Path(oldfile).stem}.qc"
    
    # Copy the content from the old file to the new file
    with open(oldfile, 'r') as infile, open(newfile, 'w') as outfile:
        for line in infile:
            # Ignore specific lines
            if 'OPENQASM 2.0;' in line or 'include "qelib1.inc";' in line:
                continue
            # Write the line to the new file
            outfile.write(line)

    # Read the contents of the new file
    with open(newfile, 'r') as file:
        content = file.read()

    # Replacement patterns
    replacements = [
        (r'qreg [^\d]*\[(\d+)\];', lambda m: f".v {' '.join(map(str, range(int(m.group(1)))))}\nBEGIN"),
        (r'h qubits\[(\d+)\];', r'H \1'),
        (r'x qubits\[(\d+)\];', r'X \1'),
        (r'y qubits\[(\d+)\];', r'Y \1'),
        (r'z qubits\[(\d+)\];', r'Z \1'),
        (r'cx qubits\[(\d+)\][^a-z]+qubits\[(\d+)\];', r'tof \1 \2'),
        (r'cz qubits\[(\d+)\][^a-z]+qubits\[(\d+)\];', r'CZ \1 \2'),
        (r's qubits\[(\d+)\];', r'S \1'),
        (r'sdg qubits\[(\d+)\];', r'S* \1'),
        (r't qubits\[(\d+)\];', r'T \1'),
        (r'tdg qubits\[(\d+)\];', r'T* \1'),
        (r'swap qubits\[(\d+)\][^a-z]+qubits\[(\d+)\];', r'Swap \1 \2'),
        (r'rz\((.+)\) qubits\[(\d+)\];', r'Rz \1 \2'),
        (r'rx\((.+)\) qubits\[(\d+)\];', r'Rx \1 \2'),
        (r'ry\((.+)\) qubits\[(\d+)\];', r'Ry \1 \2'),
        (r'ccx qubits\[(\d+)\][^a-z]+qubits\[(\d+)\][^a-z]+qubits\[(\d+)\];', r'tof \1 \2 \3'),
    ]
    

    # Apply the replacements
    for pattern, replacement in replacements:
        content = re.sub(pattern, replacement, content)
    # Append "END" to the file
    content += "END"

    # Write the modified content back to the file
    with open(newfile, 'w') as file:
        file.write(content)

    print(f"Conversion completed. Output saved to: {newfile}")


if __name__ == "__main__":
    if len(sys.argv) < 2 or len(sys.argv) > 3:
        print("Usage: python script.py <oldfile.qasm> [output_dir]")
    else:
        oldfile = sys.argv[1]
        output_dir = sys.argv[2] if len(sys.argv) == 3 else None
        convert_qasm_to_qc(oldfile, output_dir)
