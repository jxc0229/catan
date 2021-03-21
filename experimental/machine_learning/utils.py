import os

import numpy as np

DISCOUNT_FACTOR = 0.99
DATA_DIRECTORY = "data"


def get_samples_path(games_directory):
    return os.path.join(games_directory, "samples.csv.gzip")


def get_board_tensors_path(games_directory):
    return os.path.join(games_directory, "board_tensors.csv.gzip")


def get_actions_path(games_directory):
    return os.path.join(games_directory, "actions.csv.gzip")


def get_rewards_path(games_directory):
    return os.path.join(games_directory, "rewards.csv.gzip")


def get_matrices_path(games_directory):
    samples_path = get_samples_path(games_directory)
    board_tensors_path = get_board_tensors_path(games_directory)
    actions_path = get_actions_path(games_directory)
    rewards_path = get_rewards_path(games_directory)
    return samples_path, board_tensors_path, actions_path, rewards_path


def get_games_directory(key=None, version=None):
    if key in set(["V", "P", "Q"]):
        return os.path.join(DATA_DIRECTORY, key, str(version))
    else:
        return os.path.join(DATA_DIRECTORY, "random_games")


def estimate_num_samples(games_directory):
    samples_path = get_samples_path(games_directory)
    file_size = os.path.getsize(samples_path)
    size_per_sample_estimate = 3906.25  # in bytes
    estimate = file_size // size_per_sample_estimate
    print(
        "Training via generator. File Size:",
        file_size,
        "Num Samples Estimate:",
        estimate,
    )
    return estimate


def generate_arrays_from_file(
    games_directory,
    batchsize,
    label_column,
    learning="Q",
    label_threshold=None,
):
    inputs = []
    targets = []
    batchcount = 0

    samples_path, board_tensors_path, actions_path, rewards_path = get_matrices_path(
        games_directory
    )
    while True:
        with open(samples_path) as s, open(actions_path) as a, open(rewards_path) as r:
            next(s)  # skip header
            next(a)  # skip header
            rewards_header = next(r)  # skip header
            label_index = rewards_header.rstrip().split(",").index(label_column)
            for i, sline in enumerate(s):
                try:
                    srecord = sline.rstrip().split(",")
                    arecord = a.readline().rstrip().split(",")
                    rrecord = r.readline().rstrip().split(",")

                    state = [float(n) for n in srecord[:]]
                    action = [float(n) for n in arecord[:]]
                    reward = float(rrecord[label_index])
                    if label_threshold is not None and reward < label_threshold:
                        continue

                    if learning == "Q":
                        sample = state + action
                        label = reward
                    elif learning == "V":
                        sample = state
                        label = reward
                    else:  # learning == "P"
                        sample = state
                        label = action

                    inputs.append(sample)
                    targets.append(label)
                    batchcount += 1
                except Exception as e:
                    print(i)
                    print(s)
                    print(e)
                if batchcount > batchsize:
                    X = np.array(inputs, dtype="float32")
                    y = np.array(targets, dtype="float32")
                    yield (X, y)
                    inputs = []
                    targets = []
                    batchcount = 0


def get_discounted_return(game, p0, discount_factor):
    """G_t = d**1*r_1 + d**2*r_2 + ... + d**T*r_T.

    Taking r_i = 0 for all i < T. And r_T = 1 if wins
    """
    assert discount_factor <= 1
    episode_return = p0.color == game.winning_color()
    return episode_return * discount_factor ** len(game.state.actions)


def get_tournament_return(game, p0, discount_factor):
    """A way to say winning is important, no matter how long it takes, and
    getting close to winning is a secondary metric"""
    episode_return = p0.color == game.winning_color()
    episode_return = episode_return * 1000 + min(p0.actual_victory_points, 10)
    return episode_return * discount_factor ** len(game.state.actions)


def get_victory_points_return(game, p0):
    # This discount factor (0.9999) ensures a game won in less turns
    #   is better, and still a Game with 9vps is less than 10vps,
    #   no matter turns.
    episode_return = min(p0.actual_victory_points, 10)
    return episode_return * 0.9999 ** len(game.state.actions)


def populate_matrices(
    samples_df, board_tensors_df, actions_df, rewards_df, games_directory
):
    samples_path, board_tensors_path, actions_path, rewards_path = get_matrices_path(
        games_directory
    )

    # Ensure directory exists.
    if not os.path.exists(games_directory):
        os.makedirs(games_directory)

    is_first_training = not os.path.isfile(samples_path)
    samples_df.to_csv(
        samples_path,
        mode="a",
        header=is_first_training,
        index=False,
        compression="gzip",
    )
    board_tensors_df.to_csv(
        board_tensors_path,
        mode="a",
        header=is_first_training,
        index=False,
        compression="gzip",
    )
    actions_df.to_csv(
        actions_path,
        mode="a",
        header=is_first_training,
        index=False,
        compression="gzip",
    )
    rewards_df.to_csv(
        rewards_path,
        mode="a",
        header=is_first_training,
        index=False,
        compression="gzip",
    )
