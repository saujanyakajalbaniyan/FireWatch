import os
import argparse
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader
from torchvision import transforms
from PIL import Image
import copy
from tqdm import tqdm

from models_custom.cnn_lstm import CNNLSTMModel

class ImageSequenceDataset(Dataset):
    """
    Dataset class that chunks a folder of sequentially named images into sliding sequences.
    """
    def __init__(self, directory, sequence_length=5, transform=None, dummy_label=0):
        self.directory = directory
        self.sequence_length = sequence_length
        self.transform = transform
        self.dummy_label = dummy_label
        
        # Load and sort all images chronologically
        valid_exts = (".jpg", ".jpeg", ".png")
        self.image_files = sorted([f for f in os.listdir(directory) if f.lower().endswith(valid_exts)])
        
        # We need at least `sequence_length` images to form a single sequence
        if len(self.image_files) < sequence_length:
            self.sequences = []
        else:
            # Create overlapping sliding window sequences
            self.sequences = [
                self.image_files[i:i+sequence_length] 
                for i in range(len(self.image_files) - sequence_length + 1)
            ]

    def __len__(self):
        return len(self.sequences)

    def __getitem__(self, idx):
        seq_files = self.sequences[idx]
        images = []
        for f in seq_files:
            img_path = os.path.join(self.directory, f)
            try:
                img = Image.open(img_path).convert('RGB')
                if self.transform:
                    img = self.transform(img)
                images.append(img)
            except Exception as e:
                # Fallback zero tensor if image is corrupt
                images.append(torch.zeros(3, 224, 224))
        
        # Stack images across sequence length -> Shape: (sequence_length, Channels, H, W)
        seq_tensor = torch.stack(images)
        
        # For this script we will map the label based on folder name if structured, else dummy
        # e.g., if "fire" is in the directory path, label is 1 (Fire)
        if "fire" in os.path.basename(os.path.normpath(self.directory)).lower() and "no" not in os.path.basename(os.path.normpath(self.directory)).lower():
            label = 1
        elif "no_fire" in os.path.basename(os.path.normpath(self.directory)).lower() or "normal" in os.path.basename(os.path.normpath(self.directory)).lower():
            label = 0
        else:
            label = self.dummy_label
            
        return seq_tensor, torch.tensor(label, dtype=torch.long)


def train_model():
    parser = argparse.ArgumentParser(description="Train CNN-LSTM Temporal Model")
    parser.add_argument('--dataset', type=str, default=".", help="Path to chronological images dataset")
    parser.add_argument('--epochs', type=int, default=5, help="Number of training epochs")
    parser.add_argument('--batch-size', type=int, default=4, help="Batch size (number of sequences)")
    parser.add_argument('--seq-length', type=int, default=5, help="Frames per sequence")
    parser.add_argument('--lr', type=float, default=0.001, help="Learning rate")
    args = parser.parse_args()

    device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
    print(f"[Train] Using device: {device}")

    # Standard CNN transform
    transform = transforms.Compose([
        transforms.Resize((224, 224)),
        transforms.ToTensor(),
        transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
    ])

    print(f"[Train] Scanning directory: {args.dataset}")
    dataset = ImageSequenceDataset(args.dataset, sequence_length=args.seq_length, transform=transform, dummy_label=1)
    
    if len(dataset) == 0:
        print("[Train] Error: Not enough images in dataset to form sequences.")
        return
        
    dataloader = DataLoader(dataset, batch_size=args.batch_size, shuffle=True, num_workers=0)

    model = CNNLSTMModel(num_classes=2, hidden_size=256, num_layers=1).to(device)
    criterion = nn.CrossEntropyLoss()
    optimizer = optim.Adam(model.parameters(), lr=args.lr)

    best_model_wts = copy.deepcopy(model.state_dict())
    best_loss = float('inf')

    print(f"[Train] Started training on {len(dataset)} sequence chunks...")
    
    for epoch in range(args.epochs):
        model.train()
        running_loss = 0.0
        running_corrects = 0
        
        # We loop over the dataset batches
        for inputs, labels in tqdm(dataloader, desc=f"Epoch {epoch+1}/{args.epochs}"):
            inputs = inputs.to(device)
            labels = labels.to(device)

            optimizer.zero_grad()

            outputs = model(inputs)
            _, preds = torch.max(outputs, 1)
            loss = criterion(outputs, labels)

            loss.backward()
            optimizer.step()

            running_loss += loss.item() * inputs.size(0)
            running_corrects += torch.sum(preds == labels.data)

        epoch_loss = running_loss / len(dataset)
        epoch_acc = running_corrects.double() / len(dataset)

        print(f"Epoch {epoch+1}/{args.epochs} - Loss: {epoch_loss:.4f} Acc: {epoch_acc:.4f}")

        if epoch_loss < best_loss:
            best_loss = epoch_loss
            best_model_wts = copy.deepcopy(model.state_dict())
            torch.save(best_model_wts, 'cnn_lstm_best.pth')

    print("[Train] Training complete. Saved model to 'cnn_lstm_best.pth'")

if __name__ == "__main__":
    train_model()
