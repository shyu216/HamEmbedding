import pennylane as qml

qml.disable_return()  # Turn of the experimental return feature,
# see https://docs.pennylane.ai/en/stable/code/api/pennylane.enable_return.html#pennylane.enable_return

import warnings
warnings.filterwarnings("ignore")

import torch
from torch import nn
from torch.utils.data import DataLoader
from with_pennylane_torch.dataset import TinyHandwrittenDigitsDataset
from with_pennylane_torch.image_transform import DEFAULT_TRANSFORM
import time
import pytorch_lightning as pl





def nowtime():
    return str(time.strftime("%Y%m%d-%H%M%S", time.localtime()))



if __name__ == '__main__':
    """
    For remote tensorboard:
    if tensorboard haven't been started:
    ssh -L 16006:127.0.0.1:6006 peiyongw@10.100.238.77
    tensorboard --logdir=<log dir> --port=6006
    Then in local browser: 
    127.0.0.1:16006
    or
    localhost:16006
    """


    from with_pennylane_torch.torch_module_prob import RecurentQNNNoPosCodeV1
    from with_pennylane_torch.byol import BYOL
    from torch.utils.tensorboard import SummaryWriter
    import json
    import os

    log_dir = f"logs-{nowtime()}"
    checkpoint_dir = f"checkpoint/checkpoints-{nowtime()}"
    if not os.path.exists(checkpoint_dir):
        os.makedirs(checkpoint_dir)
    writer = SummaryWriter(os.path.join('runs', log_dir))

    # data paths
    img_dir = "/home/peiyongw/Desktop/Research/QML-ImageClassification/data/mini-digits/images"
    csv_file = "/home/peiyongw/Desktop/Research/QML-ImageClassification/data/mini-digits/annotated_labels.csv"

    BATCH_SIZE = 100
    EPOCHS = 100

    # structural parameters
    N_MEM_QUBITS = 4  # don't change this unless change the model structure
    N_PATCH_QUBITS = 4

    L1 = 2
    L2 = 2
    L_MC = 1
    RESET_FIRST_MEM_QUBIT = True

    model_hyperparams = {
        "L1": L1,
        "L2": L2,
        "L_MC": L_MC,
        "n_mem_qubits": N_MEM_QUBITS,
        "n_patch_qubits": N_PATCH_QUBITS,
        "forget_gate": RESET_FIRST_MEM_QUBIT
    }

    training_hyperparams = {
        "batch_size": BATCH_SIZE,
        "epochs": EPOCHS,
        "model_hyperparams": model_hyperparams
    }

    with open(os.path.join(checkpoint_dir, 'training_hyperparams.json'), 'w') as f:
        json.dump(training_hyperparams, f, indent=4)

    device = 'cpu'

    base_model = RecurentQNNNoPosCodeV1(L1, L2, L_MC, N_MEM_QUBITS, N_PATCH_QUBITS, RESET_FIRST_MEM_QUBIT)

    ssl_model = BYOL(base_model, RecurentQNNNoPosCodeV1, model_hyperparams, image_size=8, hidden_layer=-1, projection_size=256, projection_hidden_size=4096, augment_fn=DEFAULT_TRANSFORM, augment_fn2=DEFAULT_TRANSFORM, moving_average_decay=0.99, use_momentum=True)

    ssl_model = ssl_model.to(device)

    optimizer = torch.optim.Adam(ssl_model.parameters(), lr=0.01, amsgrad=True)

    dataset = TinyHandwrittenDigitsDataset(csv_file, img_dir)

    train_size = int(0.6 * len(dataset))
    val_size = int(0.2 * len(dataset))
    test_size = len(dataset) - train_size- val_size
    train_dataset, val_dataset, test_dataset = torch.utils.data.random_split(dataset, [train_size, val_size, test_size])
    train_loader, val_loader, test_loader = DataLoader(train_dataset, batch_size=BATCH_SIZE, shuffle=True, num_workers=10), \
                                            DataLoader(val_dataset, batch_size=1, shuffle=True, num_workers=10), \
                                            DataLoader(test_dataset, batch_size=1, shuffle=True, num_workers=10)

    batch_iters = 0
    all_start = time.time()
    for epoch in range(EPOCHS):
        epoch_start = time.time()
        total_loss = 0
        for i, (x, _) in enumerate(train_loader):
            batch_start = time.time()
            x = x.to(device)
            loss = ssl_model(x)
            writer.add_scalar('Loss/train_batch', loss.item(), batch_iters)
            total_loss = total_loss + loss.item()
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()
            batch_end = time.time()
            print(f"Epoch {epoch} batch {i} loss: {loss.item()} time: {batch_end - batch_start}")
            batch_iters += 1
        writer.add_scalar('Loss/train_epoch', total_loss / len(train_loader), epoch)
        print(f"Epoch {epoch} train loss: {total_loss / len(train_loader)}, train time: {time.time() - epoch_start}")
        for name, weight in ssl_model.named_parameters():
            writer.add_histogram(name, weight, epoch)
            writer.add_histogram(f'{name}.grad', weight.grad, epoch)
        if (epoch) % 10 == 0:
            checkpoint = {
                'epoch': epoch,
                'model': ssl_model.state_dict(),
                'optimizer': optimizer.state_dict()
            }
            torch.save(checkpoint, f'epoch-{str(epoch).zfill(5)}-checkpoint.pth')
            print(f"Epoch {epoch} checkpoint saved")
        if (epoch) % 10 == 0:
            total_loss = 0
            for i, (x, _) in enumerate(val_loader):
                x = x.to(device)
                loss = ssl_model(x)
                total_loss = total_loss + loss.item()
            writer.add_scalar('Loss/val_epoch', total_loss / len(val_loader), epoch)
            print(f"Epoch {epoch} val loss: {total_loss / len(val_loader)}, train + val time: {time.time() - epoch_start}")




