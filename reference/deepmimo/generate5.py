import deepmimo as dm
import numpy as np
import os
import multiprocessing
from concurrent.futures import ProcessPoolExecutor, as_completed
import time

# ==========================================
# 1. Writer 进程 (多消费者模式)
# ==========================================
def writer_listener(queue):
    """
    现在会有多个 Writer 同时运行。
    Queue 内部有锁，自动保证数据不冲突。
    """
    pid = os.getpid()
    print(f"💾 Writer process [{pid}] started...")
    
    while True:
        try:
            # 获取任务
            record = queue.get()
            
            # 结束信号检查
            if record is None:
                # 收到 None 表示该下班了
                break
                
            train_data, test_data, save_folder = record
            
            # 写入操作
            os.makedirs(save_folder, exist_ok=True)
            np.save(os.path.join(save_folder, "train.npy"), train_data)
            np.save(os.path.join(save_folder, "test.npy"), test_data)
            
            print(f"✅ [Writer {pid}] Saved: {os.path.basename(save_folder)} "
                  f"| Shape: {train_data.shape}")
                  
        except Exception as e:
            print(f"❌ [Writer {pid} Error] {save_folder if 'save_folder' in locals() else 'Unknown'}: {e}")
            import traceback
            traceback.print_exc()
            
    print(f"💾 Writer process [{pid}] finished.")

# ==========================================
# 2. 计算任务 (保持你刚才的逻辑不变)
# ==========================================
def compute_task(scen_name, save_root, queue):
    # ... (这里完全用你上一条消息提供的代码，不需要变) ...
    # 为了节省篇幅，这里简略，请直接保留你原来写好的 compute_task 即可
    try:
        # --- DeepMIMO 配置 ---
        dataset = dm.load(scen_name)
        ch_params = dm.ChannelParameters()
        ch_params.bs_antenna.shape = [8, 4]   # 32 Tx
        ch_params.bs_antenna.spacing = 0.5 
        ch_params.ue_antenna.shape = [2, 1]   # 2 Rx
        ch_params.ue_antenna.spacing = 0.5 
        ch_params.freq_domain = True
        ch_params.ofdm.bandwidth = 20e6 
        ch_params.ofdm.subcarriers = 1024
        ch_params.ofdm.selected_subcarriers = np.arange(64)
        ch_params.ofdm.rx_filter = False 

        dataset.compute_channels(ch_params)
        raw_H = dataset.channel
        
        if isinstance(raw_H, list): raw_H = np.array(raw_H)
        elif raw_H.ndim == 4: raw_H = np.expand_dims(raw_H, axis=0)
            
        num_bs, num_ue, n_rx, n_tx, n_sub = raw_H.shape

        # 步骤 1: 能量矩阵
        power_matrix = np.sum(np.abs(raw_H)**2, axis=(2, 3, 4))
        POWER_THRESHOLD = 1e-15 

        # 步骤 2: 划分用户
        perm_users = np.random.permutation(num_ue)
        split_idx = int(num_ue * 0.9)
        train_user_indices = perm_users[:split_idx]
        test_user_indices = perm_users[split_idx:]
        
        # 步骤 3: 提取与 Rx-Tx 堆叠
        def extract_valid_samples(user_indices):
            subset_power = power_matrix[:, user_indices]
            subset_H = raw_H[:, user_indices, :, :, :] 
            valid_mask = subset_power > POWER_THRESHOLD
            valid_data_raw = subset_H[valid_mask] # (N, 2, 32, 64)
            
            if valid_data_raw.shape[0] == 0: return None

            # (N, Rx, Tx, Sub) -> (N, Rx*Tx, Sub) = (N, 64, 64)
            data_stacked = valid_data_raw.reshape(-1, 64, 64)
            return data_stacked

        train_merged = extract_valid_samples(train_user_indices)
        test_merged = extract_valid_samples(test_user_indices)
        
        if train_merged is None or test_merged is None:
            # print(f"⚠️ [Skipped] {scen_name}")
            return

        # 步骤 4: 归一化处理
        def process_final(data):
            # data: (N, 64, 64)
            p = np.sum(np.abs(data)**2, axis=(1, 2))
            d = data[p > 1e-15] 
            max_vals = np.max(np.abs(d), axis=(1, 2), keepdims=True)
            max_vals[max_vals == 0] = 1.0
            d_norm = d / max_vals
            # Stack -> (N, 2, 64, 64)
            data_final = np.stack((np.real(d_norm), np.imag(d_norm)), axis=1)
            return data_final.astype(np.float32)

        train_final = process_final(train_merged)
        test_final = process_final(test_merged)

        folder_path = os.path.join(save_root, scen_name)
        queue.put((train_final, test_final, folder_path))

    except Exception as e:
        print(f"❌ [Error] {scen_name}: {e}")

# ==========================================
# 3. 主程序 (核心修改)
# ==========================================
def main():
    save_path_root = "./data_merged"
    scenarios_dir = 'deepmimo_scenarios' 
    
    if not os.path.exists(scenarios_dir):
        print(f"Error: Directory '{scenarios_dir}' not found.")
        return

    subfolders = [f.name for f in os.scandir(scenarios_dir) if f.is_dir()]
    if '28' in subfolders: subfolders.remove('28')
    print(f"Found {len(subfolders)} scenarios to process.")

    manager = multiprocessing.Manager()
    # 稍微调大 Queue 容量，让 Compute 跑得更欢
    queue = manager.Queue(maxsize=50) 

    # ------------------------------------------------
    # 配置多进程参数
    # ------------------------------------------------
    total_cpu_cores = 16
    
    # 建议配置：
    # 写入通常是 IO 密集型，不需要太多 CPU，但需要占用带宽。
    # 计算是 CPU 密集型。
    # 假设你有 16 核：给 4 个写进程，12 个算进程。
    
    NUM_WRITERS = 4  # 开启 4 个写手
    NUM_WORKERS = max(1, total_cpu_cores - NUM_WRITERS) # 剩下的全去算数
    
    print(f"🚀 Configuration: {NUM_WORKERS} Compute Workers | {NUM_WRITERS} Disk Writers")

    # ------------------------------------------------
    # 启动多个 Writer 进程
    # ------------------------------------------------
    writers = []
    for _ in range(NUM_WRITERS):
        w = multiprocessing.Process(target=writer_listener, args=(queue,))
        w.start()
        writers.append(w)

    start_time = time.time()

    # 启动计算进程池
    with ProcessPoolExecutor(max_workers=NUM_WORKERS) as executor:
        futures = []
        for scen in subfolders:
            futures.append(executor.submit(compute_task, scen, save_path_root, queue))
        
        # 监控进度
        completed_count = 0
        for future in as_completed(futures):
            try:
                future.result()
                completed_count += 1
                # print(f"Progress: {completed_count}/{len(subfolders)}")
            except Exception as exc:
                print(f"Task exception: {exc}")

    print("\n✅ All computations finished. Sending stop signals to writers...")

    # ------------------------------------------------
    # 发送结束信号 (关键步骤)
    # ------------------------------------------------
    # 有几个 Writer，就要塞几个 None 进去，
    # 这样每个 Writer 都能领到一个 None 然后下班。
    for _ in range(NUM_WRITERS):
        queue.put(None)

    # 等待所有 Writer 下班
    for w in writers:
        w.join()

    print(f"\n🎉 All tasks completed in {time.time() - start_time:.2f} seconds.")

if __name__ == '__main__':
    multiprocessing.freeze_support()
    main()