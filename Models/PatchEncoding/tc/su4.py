from functools import wraps
from typing import Any, Callable, Optional, Sequence, Tuple, List

from jax import numpy as jnp

import tensorcircuit as tc

Circuit = tc.Circuit
Tensor = jnp.array

def applySU4Gate(circ:Circuit, params:Tensor, wires:List[int])->Circuit:
    """
    Apply a SU4 gate to the circuit.
    Args:
        circ: The input circuit
        params: parameters for the SU4 gate
        wires: the qubits to be used. Number of qubits: 2

    Returns:
        the updated circuit with the SU4 gate applied to wires
    """
    circ.U(wires[0], theta = params[..., 0], phi = params[..., 1], lbd = params[..., 2])
    circ.U(wires[1], theta = params[..., 3], phi = params[..., 4], lbd = params[..., 5])
    circ.RXX(wires[0], wires[1], theta = params[..., 6])
    circ.RYY(wires[0], wires[1], theta = params[..., 7])
    circ.RZZ(wires[0], wires[1], theta = params[..., 8])
    circ.U(wires[0], theta = params[..., 9], phi = params[..., 10], lbd = params[..., 11])
    circ.U(wires[1], theta = params[..., 12], phi = params[..., 13], lbd = params[..., 14])
    return circ

def applyHeadlessSU4(circ:Circuit, params:Tensor, wires = List[int])->Circuit:
    """
    Apply a headless SU4 gate (SU4 gate without leading U gates) to the circuit.
    Args:
        circ: the circuit being updated
        params: parameters of the gate, 9 parameters
        wires: qubits to be used. Number of qubits: 2

    Returns:
        the updated circuit with the headless SU4 gate applied to wires
    """
    circ.RXX(wires[0], wires[1], theta = params[..., 0])
    circ.RYY(wires[0], wires[1], theta = params[..., 1])
    circ.RZZ(wires[0], wires[1], theta = params[..., 2])
    circ.U(wires[0], theta = params[..., 3], phi = params[..., 4], lbd = params[..., 5])
    circ.U(wires[1], theta = params[..., 6], phi = params[..., 7], lbd = params[..., 8])
    return circ

def applyTaillessSU4(circ:Circuit, params:Tensor, wires = List[int])->Circuit:
    """
    Apply a tailless SU4 gate (SU4 gate without ending U gates) to the circuit.
    Args:
        circ: the circuit being updated
        params: parameters of the gate, 9 parameters
        wires: qubits to be used. Number of qubits: 2

    Returns:
        the updated circuit with the headless SU4 gate applied to wires
    """
    circ.U(wires[0], theta = params[..., 0], phi = params[..., 1], lbd = params[..., 2])
    circ.U(wires[1], theta = params[..., 3], phi = params[..., 4], lbd = params[..., 5])
    circ.RXX(wires[0], wires[1], theta = params[..., 6])
    circ.RYY(wires[0], wires[1], theta = params[..., 7])
    circ.RZZ(wires[0], wires[1], theta = params[..., 8])
    return circ



if __name__ == '__main__':
    # test
    import jax
    import jax.numpy as jnp

    K = tc.set_backend("jax")
    circ = tc.Circuit(2)
    params = jnp.array([1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11,12, 13, 14, 15])
    circ = applySU4Gate(circ, params, [0, 1])
    circ = applyHeadlessSU4(circ, params[3:], [0, 1])
    circ = applyTaillessSU4(circ, params[:9], [0, 1])
    print(circ.to_qiskit())
    print(circ.state())