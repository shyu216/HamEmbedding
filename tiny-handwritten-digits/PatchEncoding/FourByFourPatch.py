from .FourPixelPatch import FourPixelReUpload, FourPixelAmpEnc
from pennylane.operation import Operation, AnyWires
from .SU4 import SU4, TailessSU4
import pennylane as qml

class FourByFourNestedReUpload(Operation):
    """
    Encode 16 pixels into 4 qubits;
    The 16 pixels are divided into 4 groups, each group has 4 pixels;
    pixels_len_16[0:4] is the first 2 by 2 patch;
    pixels_len_16[4:8] is the second 2 by 2 patch;
    pixels_len_16[8:12] is the third 2 by 2 patch;
    pixels_len_16[12:16] is the fourth 2 by 2 patch;
    Each group of 4 pixels is encoded into 2 qubits using 'FourPixelReUpload';
    And have different re-upload parameters for each group of 4 pixels;
    Then only for the 'FourPixelReUpload', the total number of parameters is 6*L1*4
    for a single layer of 'FourByFourPatchReUpload';
    Then the total parameter for four_pixel_encode_parameters should be in shape (...,L2, 6*L1*4)
    Plus a layer of Rot gates and CRot gates, giving us 4*3+3*3=21 parameters per layer of 'FourByFourPatchReUpload';
    Then the shape of sixteen_pixel_parameters should be (...,L2, 21)

    One re-uploading layer of FourByFourNestedReUpload starts with 4 'FourPixelReUpload' operations, two for each two qubits.
    The parameters should be in shape  6*L1*4
    Then followed by a layer of Rot gates and CRot gates.
    The parameters should be in shape 4*3+3*3=21.
    For L2 re-uploading layers, the shape for 'FourPixelReUpload' part should be (...,L2, 6*L1*4)
    And for the 4-qubit parameterized layer with Rot and CRot gates, the shape should be (...,L2, 21)
    """

    def __init__(self, pixels_len_16, four_pixel_encode_parameters, sixteen_pixel_parameters, L1, L2, wires, id=None):
        interface = qml.math.get_interface(four_pixel_encode_parameters)
        four_pixel_encode_parameters = qml.math.asarray(four_pixel_encode_parameters, like=interface)
        pixels_len_16 = qml.math.asarray(pixels_len_16, like=interface)
        sixteen_pixel_parameters = qml.math.asarray(sixteen_pixel_parameters, like=interface)

        self._hyperparameters = {"L1": L1, "L2": L2}

        pixels_len_16_shape = qml.math.shape(pixels_len_16)
        four_pixel_encode_parameters_shape = qml.math.shape(four_pixel_encode_parameters)
        sixteen_pixel_parameters_shape = qml.math.shape(sixteen_pixel_parameters)
        if not (len(pixels_len_16_shape)==1 or len(pixels_len_16_shape)==2): # 2 is when batching, 1 is not batching
            raise ValueError(f"pixels must be a 1D or 2D array; got shape {pixels_len_16_shape}")
        if pixels_len_16_shape[-1]!=16:
            raise ValueError(f"pixels must be a 1D or 2D array with last dimension 16; got shape {pixels_len_16_shape}")
        if not (len(four_pixel_encode_parameters_shape)==2 or len(four_pixel_encode_parameters_shape)==3): # 3 is when batching, 2 is not batching
            raise ValueError(f"four_pixel_encode_parameters must be a 2D or 3D array; got shape {four_pixel_encode_parameters_shape}")
        if four_pixel_encode_parameters_shape[-1]!=6*L1*4 or four_pixel_encode_parameters_shape[-2]!=L2:
            raise ValueError(f"four_pixel_encode_parameters must be a 2D or 3D array with dimension (...,{L2}, 6*{L1}*4); got shape {four_pixel_encode_parameters_shape}")
        if not (len(sixteen_pixel_parameters_shape)==2 or len(sixteen_pixel_parameters_shape)==3): # 3 is when batching, 2 is not batching
            raise ValueError(f"sixteen_pixel_parameters must be a 2D or 3D array with shape (...,{L2}, 21); got shape {sixteen_pixel_parameters_shape}")
        if sixteen_pixel_parameters_shape[-2]!=L2 or sixteen_pixel_parameters_shape[-1]!=21:
            raise ValueError(f"sixteen_pixel_parameters must be a 2D or 3D array with shape (...,{L2}, 21); got shape {sixteen_pixel_parameters_shape}")

        super().__init__(pixels_len_16, four_pixel_encode_parameters, sixteen_pixel_parameters, wires=wires,  id=id)

    @property
    def num_params(self):
        return 3

    @staticmethod
    def compute_decomposition(pixels_len_16, four_pixel_encode_parameters, sixteen_pixel_parameters, wires, L1, L2):
        op_list = []
        for i in range(L2):
            op_list.append(
                FourPixelReUpload(pixels_len_16[..., 0:4], four_pixel_encode_parameters[..., i, 0:6 * L1], L1,
                                  wires=[wires[0], wires[1]]))
            op_list.append(
                FourPixelReUpload(pixels_len_16[..., 4:8], four_pixel_encode_parameters[..., i, 6 * L1:6 * L1 * 2], L1,
                                  wires=[wires[2], wires[3]]))
            op_list.append(qml.CZ(wires=[wires[0], wires[2]]))
            op_list.append(qml.CZ(wires=[wires[1], wires[3]]))
            op_list.append(
                FourPixelReUpload(pixels_len_16[..., 8:12], four_pixel_encode_parameters[..., i, 6 * L1 * 2:6 * L1 * 3],
                                  L1,
                                  wires=[wires[0], wires[1]]))
            op_list.append(
                FourPixelReUpload(pixels_len_16[..., 12:16],
                                  four_pixel_encode_parameters[..., i, 6 * L1 * 3:6 * L1 * 4], L1,
                                  wires=[wires[2], wires[3]]))
            op_list.append(qml.CZ(wires=[wires[0], wires[2]]))
            op_list.append(qml.CZ(wires=[wires[1], wires[3]]))
            op_list.append(qml.Rot(sixteen_pixel_parameters[..., i, 0], sixteen_pixel_parameters[..., i, 1],
                                   sixteen_pixel_parameters[..., i, 2], wires=wires[0]))
            op_list.append(qml.Rot(sixteen_pixel_parameters[..., i, 3], sixteen_pixel_parameters[..., i, 4],
                                   sixteen_pixel_parameters[..., i, 5], wires=wires[1]))
            op_list.append(qml.Rot(sixteen_pixel_parameters[..., i, 6], sixteen_pixel_parameters[..., i, 7],
                                   sixteen_pixel_parameters[..., i, 8], wires=wires[2]))
            op_list.append(qml.Rot(sixteen_pixel_parameters[..., i, 9], sixteen_pixel_parameters[..., i, 10],
                                   sixteen_pixel_parameters[..., i, 11], wires=wires[3]))
            # CRot direction: 3->2, 2->1, 1->0
            op_list.append(qml.CRot(sixteen_pixel_parameters[..., i, 12], sixteen_pixel_parameters[..., i, 13],
                                    sixteen_pixel_parameters[..., i, 14], wires=[wires[3], wires[2]]))
            op_list.append(qml.CRot(sixteen_pixel_parameters[..., i, 15], sixteen_pixel_parameters[..., i, 16],
                                    sixteen_pixel_parameters[..., i, 17], wires=[wires[2], wires[1]]))
            op_list.append(qml.CRot(sixteen_pixel_parameters[..., i, 18], sixteen_pixel_parameters[..., i, 19],
                                    sixteen_pixel_parameters[..., i, 20], wires=[wires[1], wires[0]]))
            op_list.append(qml.Barrier(only_visual=True, wires=wires))
        return op_list
