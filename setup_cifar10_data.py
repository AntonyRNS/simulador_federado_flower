import os
import sys

def check_dependencies():
    """Verifica e instala dependências necessárias para o script."""
    try:
        import tensorflow
        import PIL
    except ImportError:
        print("Instalando dependências necessárias (tensorflow e pillow)...")
        import subprocess
        subprocess.check_call([sys.executable, "-m", "pip", "install", "tensorflow", "pillow"])

check_dependencies()

import numpy as np
from PIL import Image
import tensorflow as tf

def save_images_to_folders(x, y, base_dir, max_images_per_client=500):
    """
    Salva imagens do dataset CIFAR-10 organizadas por classe em subpastas.
    """
    class_names = [
        "airplane", "automobile", "bird", "cat", "deer",
        "dog", "frog", "horse", "ship", "truck"
    ]
    
    # Criar diretório base se não existir
    os.makedirs(base_dir, exist_ok=True)
    
    # Criar subpastas para cada classe
    for class_name in class_names:
        os.makedirs(os.path.join(base_dir, class_name), exist_ok=True)
        
    print(f"Salvando imagens em {base_dir}...")
    
    # Limitar o número de imagens para economizar espaço e tempo de treinamento local
    count = 0
    for idx, (img_array, label_idx) in enumerate(zip(x, y)):
        if count >= max_images_per_client:
            break
            
        label = class_names[int(label_idx)]
        img = Image.fromarray(img_array)
        img_path = os.path.join(base_dir, label, f"img_{idx}.png")
        img.save(img_path)
        count += 1
        
    print(f"Concluído! {count} imagens salvas no diretório {base_dir}.")

def main():
    print("Carregando o dataset CIFAR-10...")
    # Carrega o CIFAR-10 usando TensorFlow Keras
    (x_train, y_train), (x_test, y_test) = tf.keras.datasets.cifar10.load_data()
    
    # Dividir o conjunto de treinamento entre client 1 e client 2
    half_size = len(x_train) // 2
    
    x_client1 = x_train[:half_size]
    y_client1 = y_train[:half_size]
    
    x_client2 = x_train[half_size:]
    y_client2 = y_train[half_size:]
    
    # Salvar nos diretórios correspondentes
    save_images_to_folders(x_client1, y_client1, "data_client1", max_images_per_client=1000)
    save_images_to_folders(x_client2, y_client2, "data_client2", max_images_per_client=1000)

if __name__ == "__main__":
    main()
