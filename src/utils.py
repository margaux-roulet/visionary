### Utils
import h5py
import os
import pickle
import re

import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns

from datetime import datetime

import gdown
from sklearn.metrics import mean_squared_error, r2_score, explained_variance_score, mean_absolute_error, mean_absolute_percentage_error
from sklearn.decomposition import PCA
from scipy.stats import pearsonr

def load_it_data(path_to_data):
    """ Load IT data

    Args:
        path_to_data (str): Path to the data

    Returns:
        np.array (x6): Stimulus train/val/test; objects list train/val/test; spikes train/val
    """

    datafile = h5py.File(os.path.join(path_to_data,'IT_data.h5'), 'r')

    stimulus_train = datafile['stimulus_train'][()]
    spikes_train = datafile['spikes_train'][()]
    objects_train = datafile['object_train'][()]
    
    stimulus_val = datafile['stimulus_val'][()]
    spikes_val = datafile['spikes_val'][()]
    objects_val = datafile['object_val'][()]
    
    stimulus_test = datafile['stimulus_test'][()]
    objects_test = datafile['object_test'][()]

    ### Decode back object type to latin
    objects_train = [obj_tmp.decode("latin-1") for obj_tmp in objects_train]
    objects_val = [obj_tmp.decode("latin-1") for obj_tmp in objects_val]
    objects_test = [obj_tmp.decode("latin-1") for obj_tmp in objects_test]

    return stimulus_train, stimulus_val, stimulus_test, objects_train, objects_val, objects_test, spikes_train, spikes_val

def visualize_img(stimulus,objects,stim_idx):
    """Visualize image given the stimulus and corresponding index and the object name.

    Args:
        stimulus (array of float): Stimulus containing all the images
        objects (list of str): Object list containing all the names
        stim_idx (int): Index of the stimulus to plot
    """    
    normalize_mean=[0.485, 0.456, 0.406]
    normalize_std=[0.229, 0.224, 0.225]

    img_tmp = np.transpose(stimulus[stim_idx],[1,2,0])

    ### Go back from normalization
    img_tmp = (img_tmp*normalize_std + normalize_mean) * 255

    plt.figure()
    plt.imshow(img_tmp.astype(np.uint8),cmap='gray')
    plt.title(str(objects[stim_idx]))
    plt.show()
    return

def download_it_data(path_to_data):
    output = os.path.join(path_to_data,"IT_data.h5")
    if not os.path.exists(output):
        url = "https://drive.google.com/file/d/1s6caFNRpyR9m7ZM6XEv_e8mcXT3_PnHS/view?usp=share_link"
        gdown.download(url, output, quiet=False, fuzzy=True)
    else:
        print("File already exists. Skipping download.")

def print_data_info(stimulus_train, spikes_train):
    n_stimulus, n_channels, img_size, _ = stimulus_train.shape
    n_bins , n_neurons = spikes_train.shape
    print('The train dataset contains {} stimuli and {} IT neurons'.format(n_stimulus,n_neurons))
    print('Each stimulus have {} channels (RGB)'.format(n_channels))
    print('The size of the image is {}x{}'.format(img_size,img_size))
    print('The number of bins of neuron spiking rate is {}'.format(n_bins))

def compute_pca(X_train, X_val, n_components=1000):
    """Perform PCA on the training set, transform both training and validation sets, and return the transformed data."
    
    Args:
        X_train (numpy.ndarray): Training features.
        X_val (numpy.ndarray): Validation features.
        n_components (int): Number of principal components to keep.

    Returns:
        tuple: Transformed training and validation sets.
    """
    print("Computing PCA... ", end='', flush=True)
    pca = PCA(n_components=n_components)
    X_train = pca.fit_transform(X_train)
    X_val = pca.transform(X_val)

    print(f"done.")
    return X_train, X_val 

def get_pca(X_train, X_val, n_components=1000):

    # Define the pickle file path
    pkl_file = 'out/linear_models/pca_model.pkl'

    # Check if the pickle file exists
    if os.path.exists(pkl_file):
        print("PCA Pickle file found, variables loaded.")
        
        # Load the PCA model and transformed data from the pickle file
        with open(pkl_file, 'rb') as f:
            pca_data = pickle.load(f)
        
        # Extract the PCA model and transformed data
        X_train_pca = pca_data['X_train_pca']
        X_val_pca = pca_data['X_val_pca']

    else:
        print("PCA Pickle file does not exist.")
        
        # Compute PCA if the pickle file does not exist
        X_train_pca, X_val_pca = compute_pca(X_train,X_val,n_components)
        
        # Save the PCA model and transformed data as a pickle file
        with open(pkl_file, 'wb') as f:
            pickle.dump({'X_train_pca': X_train_pca, 'X_val_pca': X_val_pca}, f)
        
        print("PCA model and transformed data saved as pickle!")

    return X_train_pca, X_val_pca

def compute_metrics(y_true, y_pred):
    r2 = r2_score(y_true, y_pred)
    mse = mean_squared_error(y_true, y_pred)
    mae = mean_absolute_error(y_true, y_pred)
    mape = mean_absolute_percentage_error(y_true, y_pred)
    ev = explained_variance_score(y_true, y_pred,multioutput='raw_values')
    ev_avg= explained_variance_score(y_true, y_pred,multioutput='uniform_average')
    corr = np.array([pearsonr(y_true[:, i], y_pred[:, i])[0] for i in range(y_true.shape[1])])
    corr_avg = np.mean(corr)
    print(f"Scores: R2={r2:.4f}, MSE={mse:.4f}, MAE={mae:.4f}, MAPE={mape:.4f}, Explained-Variance (uniform avg)={ev_avg:.4f}, Correlation PearsonR (avg)={corr_avg:.4f}")

    return r2 ,mse, mae, mape, ev, ev_avg, corr, corr_avg

def encode_object_base_labels(objects_train):
    """
    Groups object labels by their alphabetic base name (e.g., 'car1', 'car2' → 'car'),
    then assigns an integer label to each base category.
    
    Args:
        objects_train (list or array): List of object strings like 'car1', 'banana4', 'dog2'
        
    Returns:
        label_dict (dict): Mapping from base name (e.g. 'car') to integer label
        object_labels (np.array): Array of integer labels corresponding to input
    """
    # Extract base names using regex (strip digits from end)
    base_names = [re.match(r'[a-zA-Z]+', obj).group() for obj in objects_train]
    
    # Get sorted unique base names
    unique_bases = sorted(set(base_names))
    
    # Map base name to integer label
    label_dict = {base: idx for idx, base in enumerate(unique_bases)}
    
    # Assign labels
    object_labels = np.array([label_dict[base] for base in base_names])
    
    return label_dict, object_labels

def plot_neurons_metrics(y_val, y_pred):
    """
    Plot the correlation and explained variance for each neuron in a single figure.
    """
    correlations = np.array([np.corrcoef(y_val[:, i], y_pred[:, i])[0, 1] for i in range(y_val.shape[1])])
    explained_variance = np.array([explained_variance_score(y_val[:, i], y_pred[:, i]) for i in range(y_val.shape[1])])
    
    fig, axes = plt.subplots(1, 2, figsize=(14, 6))
    
    # Correlation Scatter Plot
    axes[0].scatter(y_val.flatten(), y_pred.flatten(), alpha=0.5)
    axes[0].plot([-1, 1], [-1, 1], linestyle='--', color='red')  # Diagonal line for slope 1
    axes[0].set_xlabel("True Neural Activity")
    axes[0].set_ylabel("Predicted Neural Activity")
    axes[0].set_title("Correlation of Predicted and True Neural Activity")
    
    # Explained Variance Plot
    axes[1].bar(range(y_val.shape[1]), explained_variance)
    axes[1].set_xlabel("Neuron Index")
    axes[1].set_ylabel("Explained Variance")
    axes[1].set_title("Explained Variance of Predicted Neural Activity")
    
    plt.tight_layout()
    plt.show()

def plot_corr_ev_distribution(r_values, ev_values,fig_name): 
    """Plot the distribution of Pearson correlation coefficients and explained variance scores for all neurons.

    Args:
        r_values (numpy.ndarray): Array of Pearson correlation coefficients for each neuron.
        ev_values (numpy.ndarray): Array of explained variance scores for each neuron.
    """
    fig, ax = plt.subplots(2, 2, sharex='col', gridspec_kw={'height_ratios': [1, 3]}, figsize=(12,6))
    sns.boxplot(x=r_values, color='skyblue', ax=ax[0,0], linecolor='black', linewidth=1, width=0.5)
    ax[0, 0].set_xlabel("")
    ax[0, 0].set_ylabel("")
    ax[0, 0].set_title("Correlation Coefficient Distribution")
    sns.histplot(r_values, color='skyblue', ax=ax[1,0])
    ax[1,0].set_xlabel("Correlation Coefficient")
    ax[1,0].set_ylabel("Frequency")
    sns.boxplot(x=ev_values, color='coral', ax=ax[0,1], linecolor='black', linewidth=1, width=0.5)
    ax[0, 1].set_xlabel("")
    ax[0, 1].set_ylabel("")
    ax[0, 1].set_title("Explained Variance Distribution")
    sns.histplot(ev_values, color='coral', ax=ax[1,1])
    ax[1,1].set_xlabel("Explained Variance")
    ax[1,1].set_ylabel("Frequency")
    plt.tight_layout()
    plt.show()

    # save figure
    # print datetime in format YYYYMMDDHHMM
    
    now = datetime.now()
    dt_string = now.strftime("%Y%m%d%H%M")
    fig.savefig(f'out/linear_models/{dt_string}_{fig_name}.png', dpi=300)
    print(f"Plot saved in : out/linear_models/{dt_string}_{fig_name}.png")
