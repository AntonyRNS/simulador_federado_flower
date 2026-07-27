import os
import numpy as np

def create_cnn_model(input_shape=(32, 32, 3), num_classes=10):
    """
    Cria e compila uma arquitetura de Rede Neural Convolucional (CNN) simples
    utilizando TensorFlow/Keras para o treinamento federado.
    """
    # Importação tardia para evitar erro caso o TensorFlow não esteja instalado
    # na máquina local durante a inicialização de outros módulos.
    import tensorflow as tf
    from tensorflow.keras import layers, models

    model = models.Sequential([
        layers.Input(shape=input_shape),
        layers.Conv2D(32, (3, 3), activation='relu'),
        layers.MaxPooling2D((2, 2)),
        layers.Conv2D(64, (3, 3), activation='relu'),
        layers.MaxPooling2D((2, 2)),
        layers.Flatten(),
        layers.Dense(64, activation='relu'),
        layers.Dense(num_classes, activation='softmax')
    ])

    model.compile(
        optimizer='adam',
        loss='sparse_categorical_crossentropy',
        metrics=['accuracy']
    )
    
    return model

def load_data_from_dir(data_dir, image_size=(32, 32)):
    """
    Carrega imagens de um diretório local e as converte em datasets NumPy
    para treinamento do modelo.
    
    O diretório deve seguir a estrutura de subpastas por classe, por exemplo:
    data_dir/
      ├── classe_a/
      │     ├── img1.jpg
      │     └── img2.jpg
      └── classe_b/
            ├── img3.jpg
            └── img4.jpg
    """
    import tensorflow as tf
    
    if not os.path.exists(data_dir):
        raise ValueError(f"Diretório de dados não encontrado: {data_dir}")
        
    # Carrega o dataset de imagens usando utilitários do Keras
    dataset = tf.keras.utils.image_dataset_from_directory(
        data_dir,
        image_size=image_size,
        batch_size=32,
        shuffle=True
    )
    
    # Extrai os dados em arrays numpy (compatíveis com NumPyClient do Flower)
    x_list = []
    y_list = []
    
    for images, labels in dataset:
        x_list.append(images.numpy())
        y_list.append(labels.numpy())
        
    if not x_list:
        raise ValueError(f"Nenhuma imagem encontrada no diretório: {data_dir}")
        
    x = np.concatenate(x_list, axis=0) / 255.0  # Normalização
    y = np.concatenate(y_list, axis=0)
    
    return x, y
