from .FourPixelPatch import FourPixelReUpload, FourPixelAmpEnc
from pennylane.operation import Operation, AnyWires
from .SU4 import SU4, TailLessSU4
import pennylane as qml

class FourByFourPatchNestedReUpload(Operation):
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

class FourByFourPatchAmpEnc(Operation):
    """
    Encode 16 pixels with Amplitude encoding.
    Then followed by a layer of U3 gate on each qubit, 12*L2 parameters
    Then (repeated) layers of headless SU4 gates, starting from bottom to the top: 3->2, 2->1, 1->0
    The total number of parameters is 12*L2+9*3*L2
    If, for some devices, Amplitude encoding can only be the leading layer, then L2=1
    """
    num_wires = 4
    grad_method = None

    def __init__(self, pixels_len_16, u3_parameters, su4_parameters, wires,L2 , id=None):
        interface = qml.math.get_interface(u3_parameters)
        u3_parameters = qml.math.asarray(u3_parameters, like=interface)
        pixels_len_16 = qml.math.asarray(pixels_len_16, like=interface)
        su4_parameters = qml.math.asarray(su4_parameters, like=interface)

        self._hyperparameters = {"L2": L2}

        pixels_len_16_shape = qml.math.shape(pixels_len_16)
        u3_parameters_shape = qml.math.shape(u3_parameters)
        su4_parameters_shape = qml.math.shape(su4_parameters)

        if not (len(pixels_len_16_shape) == 1 or len(
                pixels_len_16_shape) == 2):  # 2 is when batching, 1 is not batching
            raise ValueError(f"pixels must be a 1D or 2D array; got shape {pixels_len_16_shape}")
        if pixels_len_16_shape[-1] != 16:
            raise ValueError(f"pixels must be a 1D or 2D array with last dimension 16; got shape {pixels_len_16_shape}")
        if not (len(u3_parameters_shape) == 2 or len(u3_parameters_shape) == 1):
            raise ValueError(f"u3_parameters must be a 1D or 2D array; got shape {u3_parameters_shape}")
        if u3_parameters_shape[-1] != 12*L2:
            raise ValueError(f"u3_parameters must be a 1D or 2D array with last dimension 12*{L2}; got shape {u3_parameters_shape}")
        if not (len(su4_parameters_shape) == 2 or len(su4_parameters_shape) == 1):  # 2 is when batching, 1 is not batching
            raise ValueError(f"su4_parameters must be a 1D or 2D array; got shape {su4_parameters_shape}")
        if su4_parameters_shape[-1] != 9*3*L2:
            raise ValueError(f"su4_parameters must be a 1D or 2D array with last dimension 9*3*{L2}; got shape {su4_parameters_shape}")
        if L2!=1:
            raise ValueError(f"Currently only support L2=1; got {L2}")

        super().__init__(pixels_len_16, u3_parameters, su4_parameters, wires=wires,  id=id)

    @property
    def num_params(self):
        return 3

    @staticmethod
    def compute_decomposition(pixels_len_16, u3_parameters, su4_parameters, wires, L2):
        op_list=[]
        for i in range(L2):
            op_list.append(qml.AmplitudeEmbedding(pixels_len_16[...,:], wires=wires,normalize=True))
            op_list.append(qml.U3(u3_parameters[..., 0+12*i], u3_parameters[..., 1+12*i], u3_parameters[..., 2+12*i], wires=wires[0]))
            op_list.append(qml.U3(u3_parameters[..., 3+12*i], u3_parameters[..., 4+12*i], u3_parameters[..., 5+12*i], wires=wires[1]))
            op_list.append(qml.U3(u3_parameters[..., 6+12*i], u3_parameters[..., 7+12*i], u3_parameters[..., 8+12*i], wires=wires[2]))
            op_list.append(qml.U3(u3_parameters[..., 9+12*i], u3_parameters[..., 10+12*i], u3_parameters[..., 11+12*i], wires=wires[3]))
            op_list.append(qml.Barrier(only_visual=True, wires=wires))
            op_list.append(SU4(su4_parameters[..., 0+27*i:9+27*i], wires=[wires[3], wires[2]], leading_gate=False))
            op_list.append(SU4(su4_parameters[..., 9+27*i:18+27*i], wires=[wires[2], wires[1]], leading_gate=False))
            op_list.append(SU4(su4_parameters[..., 18+27*i:27+27*i], wires=[wires[1], wires[0]], leading_gate=False))
            op_list.append(qml.Barrier(only_visual=True, wires=wires))
        return op_list

def sixteen_param_circuit(params, wires):
    """
    3-qubit circuit with 16 parameters
    :param params:
    :param wires:
    :return:
    """
    qml.U3(params[...,0], params[...,1], params[...,2], wires=wires[0])
    qml.U3(params[...,3], params[...,4], params[...,5], wires=wires[1])
    qml.U3(params[...,6], params[...,7], params[...,8], wires=wires[2])
    qml.IsingXX(params[...,9], wires=[wires[0], wires[1]])
    qml.IsingYY(params[...,10], wires=[wires[0], wires[1]])
    qml.IsingZZ(params[...,11], wires=[wires[0], wires[1]])
    qml.IsingXX(params[...,12], wires=[wires[1], wires[2]])
    qml.IsingYY(params[...,13], wires=[wires[1], wires[2]])
    qml.IsingZZ(params[...,14], wires=[wires[1], wires[2]])
    qml.IsingXX(params[...,15], wires=[wires[0], wires[2]])

class FourByFourDirectReUploading(Operation):
    """
    Encode 16 pixels into 3 qubits;
    Pixel values are encoded using a 3-qubit, 16-parameter circuit;
    Then followed by 2 tailless SU4 gates, starting from bottom to the top:  2->1, 1->0
    The total number of trainable parameters is 9*3*L2
    where L2 is the number of re-uploading layers
    """
    num_wires = 3
    grad_method = None

    def __init__(self, pixels, params, wires, L2, id=None):
        """

        :param pixels: input pixel data. 16 element array (flattend from 4 by 4 patch)
        :param params: trainable parameters for encoding. 9*2*L2 element array
        :param wires: 3 qubits
        :param L2: number of re-uploading repetitions
        :param id:
        """
        interface = qml.math.get_interface(params)
        params = qml.math.asarray(params, like=interface)
        pixels = qml.math.asarray(pixels, like=interface)
        params_shape = qml.math.shape(params)
        pixels_shape = qml.math.shape(pixels)

        if not (len(pixels_shape)==1 or len(pixels_shape)==2):
            raise ValueError(f"pixels must be a 1D or 2D array; got shape {pixels_shape}")

        if pixels_shape[-1]!=16:
            raise ValueError(f"pixels must be a 1D or 2D array with last dimension 16; got shape {pixels_shape}")

        if not (len(params_shape)==1 or len(params_shape)==2):
            raise ValueError(f"params must be a 1D or 2D array; got shape {params_shape}")

        if params_shape[-1]!=9*2*L2:

            raise ValueError(f"params must be a 1D or 2D array with last dimension 9*2*{L2}; got shape {params_shape}")

        self._hyperparameters = {"L2": L2}

        super().__init__(pixels, params, wires=wires,  id=id)

    @property
    def num_params(self):
        return 3

    @staticmethod
    def compute_decomposition(pixels, params, wires, L2):
        op_list = []
        for i in range(L2):
            op_list.append(sixteen_param_circuit(pixels[...,:], wires))
            op_list.append(qml.Barrier(only_visual=True, wires=wires))
            op_list.append(TailLessSU4(params[..., 0+18*i:9+18*i], wires=[wires[2], wires[1]]))
            op_list.append(TailLessSU4(params[..., 9+18*i:18+18*i], wires=[wires[1], wires[0]]))
            op_list.append(qml.Barrier(only_visual=True, wires=wires))
            op_list.append(qml.Barrier(only_visual=True, wires=wires))
        return op_list



if __name__ == '__main__':
    import matplotlib.pyplot as plt
    import torch

    dev4q = qml.device('default.qubit', wires=3)

    L2=2

    @qml.qnode(dev4q, interface='torch')
    def circuit(pixels, params):
        FourByFourDirectReUploading.compute_decomposition(pixels,params, wires=[0,1,2], L2=L2)
        return qml.probs(wires=[0,1,2])


    pixels_16 = torch.randn(3, 16)
    params = torch.randn( 9*2*L2)
    print(circuit(pixels_16, params))
    fig, ax = qml.draw_mpl(circuit, style='sketch')(pixels_16[0], params)
    fig.savefig('four_by_four_patch_direct_reuploading.png')
    plt.close(fig)