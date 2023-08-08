import datetime
import sys
import random
import logging
from FrontEnd import config

# Basic logging configuration
logging.basicConfig(
    level=logging.ERROR,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def subInvalidateKey(image_key):
    """
    Delete a key from the memcache if it exists.
    
    Parameters:
        image_key (str): The key to be invalidated in the memcache.

    Returns:
        bool: True if the key is deleted from the memcache, otherwise False.

    Description:
        This function removes a key from the memcache if it exists. It is used to invalidate
        a key when it is no longer needed or to free up space in the cache.
    """
    try:
        if image_key in config.memcache:
            config.total_image_size = config.total_image_size - sys.getsizeof(config.memcache[image_key]['content'])
            config.memcache.pop(image_key, None)
        return True
    except Exception as e:
        # Log the exception and return False
        logging.error(f"Error in subInvalidateKey: {e}")
        return False


"""REPLACEMENT POLICY"""


def dictLRU():
    """
    Least Recently Used (LRU) replacement policy: Remove the "oldest" key from memcache.

    Description:
        This function implements the LRU replacement policy to remove the "oldest" key from
        the memcache based on the timestamp associated with each key. The LRU policy removes
        the least recently used key to make space for new keys when the cache capacity is full.
    """
    OldTimeStamp = min([d['time'] for d in config.memcache.values()])
    oldestKey = ""
    for image_key in config.memcache.keys():
        if config.memcache[image_key]['time'] == OldTimeStamp:
            oldestKey = image_key  # find oldest key
    # image size deducted
    config.total_image_size = config.total_image_size - sys.getsizeof(config.memcache[oldestKey]['content'])
    del config.memcache[oldestKey]  # delete oldest key


def dictRandom():
    """
    Random replacement policy: Remove a key randomly from memcache.

    Description:
        This function implements the random replacement policy to remove a key randomly from
        the memcache when the cache capacity is full. It randomly selects a key and deletes it
        to make space for new keys.
    """
    keys = list(config.memcache.keys())
    keyIndex = random.randint(0, len(keys) - 1)
    # image size deducted
    config.total_image_size = config.total_image_size - sys.getsizeof(config.memcache[keys[keyIndex]]['content'])
    del config.memcache[keys[keyIndex]]  # delete the random key


"""///CAPACITY CONTROL///"""


def fitCapacity(extraSize):
    """
    Ensure the memcache capacity is not exceeded by deleting keys based on the selected policy.

    Parameters:
        extraSize (int): The size of the new data to be added to the memcache.

    Description:
        This function checks if adding new data to the memcache will exceed the cache capacity.
        If it does, it removes keys from the memcache based on the selected replacement policy
        (either LRU or random) until enough space is available for the new data.
    """
    while (extraSize + config.total_image_size) > config.memcacheConfig['capacity'] * 1048576 and bool(config.memcache):
        # capacity full
        if config.memcacheConfig['policy'] == "LRU":
            dictLRU()
        else:
            dictRandom()


"""///FUNCTION PUT KEY FOR MEMCACHE"""


def subPUT(image_key, value):
    """
    Add a key-value pair to the memcache while ensuring the capacity is not exceeded.

    Parameters:
        image_key (str): The key associated with the image data.
        value (str): The base64-encoded image data.

    Returns:
        bool: True if the key-value pair is successfully added to the memcache, otherwise False.

    Description:
        This function adds a key-value pair to the memcache while ensuring that the cache capacity
        is not exceeded. If the image data size exceeds the cache capacity, the function returns False.
        Otherwise, it adds the key-value pair to the cache using the specified replacement policy (LRU or random).
    """
    try:
        if not value:
            return False

        image_size = sys.getsizeof(value)
        if image_size > config.memcacheConfig['capacity'] * 1048576:
            return False

        fitCapacity(image_size)
        config.memcache[image_key] = {'content': value, 'time': datetime.datetime.now()}
        config.total_image_size = config.total_image_size + image_size
        return True
    except Exception as e:
        # Log the exception and return False
        logging.error(f"Error in subPUT: {e}")
        return False


"""///FUNCTION GRT KEY FOR MEMCACHE///"""


def subGET(image_key):
    """
    Retrieve image data from the memcache and update its timestamp.

    Parameters:
        image_key (str): The key associated with the image data.

    Returns:
        str or False: The base64-encoded image data if the key exists in the memcache, otherwise False.

    Description:
        This function retrieves the image data from the memcache using the provided key. If the key exists,
        it updates the timestamp of the key to indicate that it has been accessed recently. If the key is not
        found in the memcache, the function returns False, indicating a cache miss.
    """
    try:
        if image_key in config.memcache.keys():
            config.memcache[image_key]['time'] = datetime.datetime.now()
            return config.memcache[image_key]['content']
        else:
            return False
    except Exception as e:
        # Log the exception and return False
        logging.error(f"Error in subGET: {e}")
        return False

"""///FUNCTION CLEAN KEY AND CONTENT FOR MEMCACHE///"""


def subCLEAR():
    """
    Clear all data from the memcache.

    Returns:
        bool: True if the memcache is successfully cleared, otherwise False.

    Description:
        This function clears all data from the memcache, including all key-value pairs and resets the total
        image size in the cache to zero. It is used when a user wants to clear all cached images and data.
    """
    try:
        config.total_image_size = 0
        config.memcache.clear()
        return True
    except Exception as e:
        # Log the exception and return False
        logging.error(f"Error in subCLEAR: {e}")
        return False
