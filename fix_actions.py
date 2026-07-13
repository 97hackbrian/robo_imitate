#!/usr/bin/env python3
"""
fix_actions.py — Recalcula TODAS las acciones de los episodios existentes
de inv(curr) @ GOAL  →  inv(curr) @ NEXT_FRAME

Uso:
    python3 fix_actions.py DATA
"""
import os
import sys
import numpy as np
import transforms3d as t3d


def parse_pose_line(line):
    """Convierte una línea '[x, y, z, r, p, y]' a una matriz 4x4."""
    vals = [float(v) for v in line.strip().strip('[]').split(',')]
    xyz = vals[:3]
    rpy = vals[3:6]
    rot = t3d.euler.euler2mat(*rpy)
    return t3d.affines.compose(xyz, rot, [1, 1, 1])


def mat_to_action_str(mat):
    """Convierte una matriz 4x4 en string de acción '[tx, ty, tz, r, p, y]'."""
    translation = mat[:3, 3]
    rotation = t3d.euler.mat2euler(mat[:3, :3])
    pose = np.concatenate((translation, rotation))
    return '[{}]'.format(', '.join(map(str, pose))) + '\n'


def fix_episode_actions(obs_path, action_path):
    """Recalcula las acciones para un episodio usando inv(curr) @ NEXT."""
    with open(obs_path, 'r') as f:
        obs_lines = [l.strip() for l in f.readlines() if l.strip()]

    observations = [parse_pose_line(l) for l in obs_lines]
    n = len(observations)

    new_actions = []
    for idx in range(n):
        curr = observations[idx]
        if idx < n - 1:
            nxt = observations[idx + 1]
        else:
            nxt = curr  # último frame: acción identidad (sin movimiento)
        action = np.linalg.inv(curr) @ nxt
        new_actions.append(mat_to_action_str(action))

    # Backup original
    backup_path = action_path + '.bak'
    if not os.path.exists(backup_path):
        os.rename(action_path, backup_path)
    else:
        os.remove(action_path)

    with open(action_path, 'w') as f:
        f.writelines(new_actions)

    return n


def main():
    if len(sys.argv) < 2:
        print("Uso: python3 fix_actions.py <DATA_DIR>")
        print("Ejemplo: python3 fix_actions.py DATA")
        sys.exit(1)

    data_dir = sys.argv[1]
    obs_dir = os.path.join(data_dir, 'observations')
    act_dir = os.path.join(data_dir, 'actions')

    if not os.path.isdir(obs_dir) or not os.path.isdir(act_dir):
        print(f"[ERROR] No se encontró {obs_dir} o {act_dir}")
        sys.exit(1)

    episodes = sorted([f[:-4] for f in os.listdir(act_dir) if f.endswith('.txt')])
    print(f"Encontrados {len(episodes)} episodios en {data_dir}")

    total_frames = 0
    for ep in episodes:
        obs_path = os.path.join(obs_dir, ep + '.txt')
        act_path = os.path.join(act_dir, ep + '.txt')

        if not os.path.exists(obs_path):
            print(f"  [SKIP] {ep}: no se encontró observaciones")
            continue

        n = fix_episode_actions(obs_path, act_path)
        total_frames += n
        print(f"  [OK] {ep}: {n} acciones recalculadas")

    print(f"\nTotal: {total_frames} acciones recalculadas en {len(episodes)} episodios.")


if __name__ == '__main__':
    main()
