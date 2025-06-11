from QuPRS.pathsum import PathSum

def support_gate_set():
    return ('h','x','y','z', 'p', 's','sdg', 't','tdg','sx','sxdg',
            'rx', 'ry','rz', 'u','u1','u2','u3',
            'cx','ch','cz','cp','ccx','mcx',
            'crx','cry','crz','cu1','cu3','cu',
            'swap','barrier','measure' )

def gate_map(circuit:PathSum, gate_name:str, qubit, gate_params = [], is_bra: bool =False, debug = False):
    if debug:
        print('add gate: %s, %s, %s, %s'%(gate_name, qubit, gate_params, is_bra))
        print('circuit in',circuit) 

    assert gate_name in support_gate_set(), 'Not support %s gate yet.'%gate_name
    if gate_name in ['barrier','measure']:
        return circuit
    func = getattr(circuit, gate_name)
    if gate_params == []:
        circuit = func(*qubit, is_bra)
    else:
        circuit = func(*gate_params, *qubit, is_bra)
    
    if debug:
        print('circuit out', circuit)
    return circuit
