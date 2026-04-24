import numpy as np
import pygame as pg
import random
import time
import copy
import os

# ===============================
# 基本参数
# ===============================
os.environ['SDL_VIDEO_WINDOW_POS'] = "%d,%d" % (20,80)

w_size = 720
pad = 36
tri_span = 15   # 15 边三角棋盘

color_line = [153, 153, 153]
color_board = [241, 196, 15]
color_black = [0, 0, 0]
color_white = [255, 255, 255]
color_dark_gray = [75, 75, 75]
color_light_gray = [235, 235, 235]
color_red = [255, 0, 0]
color_green = [0, 255, 0]

sep_x = sep_y = pad_x = pad_y = piece_radius = 0

# 三角棋盘“几何中心”
TRI_CENTER = ((tri_span - 1) / 3.0, (tri_span - 1) / 3.0)


# ===============================
# 绘制棋盘
# ===============================
def draw_board():
    global sep_x, sep_y, pad_x, pad_y, piece_radius

    sep_x = (w_size - 2 * pad) / (tri_span - 1)
    sep_y = sep_x * np.sqrt(3) / 2
    pad_x = pad
    pad_y = w_size / 2 - (w_size - 2 * pad) * np.sqrt(3) / 4
    piece_radius = sep_x * 0.3

    surface = pg.display.set_mode((w_size, w_size))
    pg.display.set_caption("Gomoku (Triangular) — final_v7")
    surface.fill(color_board)

    for i in range(tri_span):
        pg.draw.line(surface, color_line,
                     (pad + i * sep_x / 2, pad_y + i * sep_y),
                     (w_size - pad - i * sep_x / 2, pad_y + i * sep_y), 3)

        pg.draw.line(surface, color_line,
                     (pad_x + i * sep_x, pad_y),
                     (w_size - pad - (tri_span - i - 1) * sep_x / 2,
                      pad_y + (tri_span - i - 1) * sep_y), 3)

        pg.draw.line(surface, color_line,
                     (w_size - pad_x - i * sep_x, pad_y),
                     (pad + (tri_span - i - 1) * sep_x / 2,
                      pad_y + (tri_span - i - 1) * sep_y), 3)

    pg.display.update()
    return surface


def click2index(pos):
    if ((pos[1] > pad_y - piece_radius) and
        (pos[0] - pad_x) > (pos[1] - pad_y - piece_radius) / np.sqrt(3) and
        (pos[0] - w_size + pad_x) < (pad_y + piece_radius - pos[1]) / np.sqrt(3)):

        u = round((pos[1] - pad_y) / sep_y)
        v = round((pos[0] - pad_x - u * sep_x / 2) / sep_x)
        return (u, v)
    return None


def draw_stone(surface, pos, color=0):
    x = pad_x + pos[0] * sep_x / 2 + pos[1] * sep_x
    y = pad_y + pos[0] * sep_y

    if color == 1:
        pg.draw.circle(surface, color_black, [x, y], piece_radius, 0)
        pg.draw.circle(surface, color_dark_gray, [x, y], piece_radius, 2)
    else:
        pg.draw.circle(surface, color_white, [x, y], piece_radius, 0)
        pg.draw.circle(surface, color_light_gray, [x, y], piece_radius, 2)
    pg.display.update()


def draw_highlighted_stone(surface, pos, color=0):
    x = pad_x + pos[0] * sep_x / 2 + pos[1] * sep_x
    y = pad_y + pos[0] * sep_y

    if color == 1:
        pg.draw.circle(surface, color_black, [x, y], piece_radius, 0)
        pg.draw.circle(surface, color_red, [x, y], piece_radius, 3)
    else:
        pg.draw.circle(surface, color_white, [x, y], piece_radius, 0)
        pg.draw.circle(surface, color_red, [x, y], piece_radius, 3)
    pg.display.update()


def print_text(surface, msg, color=color_black):
    pg.draw.rect(surface, color_board,
                 pg.Rect(0, 0, w_size, pad_y - piece_radius - 5), 0)
    font = pg.font.SysFont('arial', 28)
    text = font.render(msg, True, color)
    surface.blit(text, (10, 10))
    pg.display.update()


def print_winner(surface, winner):
    if winner == 1:
        print_text(surface, "Black wins!", color_black)
    elif winner == -1:
        print_text(surface, "White wins!", color_white)
    elif winner == 2:
        print_text(surface, "Draw — White wins", color_line)


# ===============================
# 胜负判断
# ===============================
def check_winner(board):
    rows, cols = board.shape
    dirs = [(0, 1), (1, 0), (1, -1)]

    for r in range(rows):
        for c in range(cols):
            if board[r, c] == 0 or board[r, c] == 5:
                continue

            player = board[r, c]

            for dr, dc in dirs:
                cnt = 0
                for k in range(6):
                    nr = r + k * dr
                    nc = c + k * dc
                    if 0 <= nr < rows and 0 <= nc < cols and board[nr, nc] == player:
                        cnt += 1
                    else:
                        break
                if cnt == 5:
                    pr = r - dr
                    pc = c - dc
                    if 0 <= pr < rows and 0 <= pc < cols and board[pr, pc] == player:
                        continue
                    return player

    if not np.any(board == 0):
        return 2
    return 0


def get_valid_positions(board):
    return list(zip(*np.where(board == 0)))


# ===============================
# quick_evaluate — 活四 / 冲四 / 活三 / 眠三 / 各种跳三
# ===============================
def quick_evaluate(board, move, player):
    """
    返回：
      live_four, rush_four, live_three, sleep_three,
      jump_three, turn_three, killer_three
    """
    if board[move] != 0:
        return 0, 0, 0, 0, 0, 0, 0

    rows, cols = board.shape
    dirs = [(0, 1), (1, 0), (1, -1)]

    board[move] = player

    live_four = rush_four = live_three = sleep_three = 0
    jump_three = turn_three = killer_three = 0

    LIVE4_6 = [
        [0,1,1,1,1,0],
    ]
    RUSH4_5 = [
        [1,1,1,1,0],
        [0,1,1,1,1],
        [1,1,0,1,1],
        [1,0,1,1,1],
        [1,1,1,0,1],
    ]
    LIVE3_5 = [
        [0,1,1,1,0],
    ]
    JUMP3_5 = [
        [1,0,1,0,1],
        [0,1,1,0,1],
        [1,0,1,1,0],
        [0,1,0,1,1],
        [1,0,0,1,1],
        [1,1,0,0,1],
    ]
    TURN3_7 = [
        [0,1,1,0,0,1,0],
        [0,1,0,0,1,1,0],
    ]
    KILL3_7 = [
        [0,1,0,1,0,1,0],
    ]

    for dr, dc in dirs:
        line = []
        for k in range(-6, 7):
            nr = move[0] + k * dr
            nc = move[1] + k * dc
            if 0 <= nr < rows and 0 <= nc < cols and board[nr, nc] != 5:
                if board[nr, nc] == player:
                    line.append(1)
                elif board[nr, nc] == 0:
                    line.append(0)
                else:
                    line.append(-1)
            else:
                line.append(-2)

        n = len(line)
        for i in range(n - 6):
            w7 = line[i:i+7]
            w6 = w7[:-1]
            w5 = w7[1:6]

            if w6 in LIVE4_6:
                live_four += 1

            if w5 in RUSH4_5:
                rush_four += 1

            if w5 in LIVE3_5:
                live_three += 1

            if w5 in JUMP3_5:
                jump_three += 1

            if w7 in TURN3_7:
                turn_three += 1

            if w7 in KILL3_7:
                killer_three += 1

            # 眠三：有 111 且两端不是同时 0
            for j in range(5):
                seg = w7[j:j+3]
                if seg == [1,1,1]:
                    left = w7[j-1] if j-1 >= 0 else -2
                    right = w7[j+3] if j+3 < 7 else -2
                    if not (left == 0 and right == 0):
                        sleep_three += 1

    board[move] = 0
    return live_four, rush_four, live_three, sleep_three, jump_three, turn_three, killer_three


# ===============================
# 复合冲四检测
# ===============================
def is_compound_rush_four(board, move, player):
    if board[move] != 0:
        return False

    board[move] = player
    lf, rf, lt, st, jt, tt, kt = quick_evaluate(board, move, player)
    board[move] = 0

    if rf == 0:
        return False

    extra = 0
    if rf >= 2: extra += 1
    if lt > 0: extra += 1
    if jt > 0: extra += 1
    if tt > 0: extra += 1
    if kt > 0: extra += 1

    return extra > 0


# ===============================
# 邻居密度
# ===============================
def count_neighbors(board, move, radius=2):
    rows, cols = board.shape
    r0, c0 = move
    cnt = 0
    for dr in range(-radius, radius+1):
        for dc in range(-radius, radius+1):
            if dr == 0 and dc == 0:
                continue
            nr = r0 + dr
            nc = c0 + dc
            if 0 <= nr < rows and 0 <= nc < cols:
                if board[nr, nc] != 0 and board[nr, nc] != 5:
                    cnt += 1
    return cnt


# ===============================
# 评分函数
# ===============================
def evaluate_move(board, move, player):
    if board[move] != 0:
        return -1e18

    score = 0

    # === 自己棋形 ===
    lf, rf, lt, st, jt, tt, kt = quick_evaluate(board, move, player)
    score += lf * 10000
    score += rf * 5000
    score += lt * 1200
    score += st * 400
    score += jt * 1800
    score += tt * 1400
    score += kt * 900

    if is_compound_rush_four(board, move, player):
        score += 2500

    # === 对手棋形（防守） ===
    op = -player
    op_lf, op_rf, op_lt, op_st, op_jt, op_tt, op_kt = quick_evaluate(board, move, op)
    score += op_lf * 20000
    score += op_rf * 10000
    score += op_lt * 3000
    score += op_st * 300
    score += op_jt * 1500
    score += op_tt * 1200
    score += op_kt * 800

    # === 三角棋盘真实中心 ===
    cr, cc = TRI_CENTER
    distc = abs(move[0] - cr) + abs(move[1] - cc)
    score -= distc * 6

    # === 三条边：u=0, v=0, u+v=tri_span-1 ===
    u, v = move
    dist_edge = min(
        u,
        v,
        (tri_span - 1) - (u + v)
    )
    score += dist_edge * 4

    # === 邻居密度 ===
    score += count_neighbors(board, move) * 25

    return score


# ===============================
# 对手活三检测 & 挡哪一侧
# ===============================
def find_opponent_live_three_blocks(board, opponent):
    rows, cols = board.shape
    dirs = [(0,1),(1,0),(1,-1)]
    results = []

    for r in range(rows):
        for c in range(cols):
            if board[r,c] != opponent:
                continue

            for dr,dc in dirs:
                coords = []
                window = []
                for k in range(5):
                    nr = r + k*dr
                    nc = c + k*dc
                    coords.append((nr,nc))
                    if 0<=nr<rows and 0<=nc<cols and board[nr,nc] != 5:
                        if board[nr,nc] == opponent:
                            window.append(1)
                        elif board[nr,nc] == 0:
                            window.append(0)
                        else:
                            window.append(-1)
                    else:
                        window.append(-1)

                if window == [0,1,1,1,0]:
                    left = coords[0]
                    right = coords[-1]
                    results.append([left, right])

    return results


def choose_best_block(board, player, blocks):
    best = None
    best_s = -1e18
    for pos in blocks:
        if board[pos] != 0:
            continue
        s = evaluate_move(board, pos, player)
        if s > best_s:
            best_s = s
            best = pos
    return best


# ===============================
# 即时决策
# ===============================
def immediate_decision(board, player):
    opponent = -player
    valid = get_valid_positions(board)

    # Step1 自己一步赢
    for mv in valid:
        board[mv] = player
        if check_winner(board) == player:
            board[mv] = 0
            return mv
        board[mv] = 0

    # Step2 挡对手一步赢
    for mv in valid:
        board[mv] = opponent
        if check_winner(board) == opponent:
            board[mv] = 0
            return mv
        board[mv] = 0

    # Step3 强攻判定（必须“双威胁”才算强攻）
    has_strong_attack = False
    for mv in valid:
        lf, rf, lt, st, jt, tt, kt = quick_evaluate(board, mv, player)
        attack_score = lf*3 + rf*2 + lt + jt + tt + kt
        if attack_score >= 2:
            has_strong_attack = True
            break

    # Step4 自己两步必胜（双威胁近似）
    def threat_score(lf, rf, lt, st, jt, tt, kt):
        return lf*3 + rf*2 + lt + jt + tt + kt

    best_two_win_mv = None
    best_two_win_score = -1e18

    for mv in valid:
        board[mv] = player
        lf, rf, lt, st, jt, tt, kt = quick_evaluate(board, mv, player)
        board[mv] = 0

        ts = threat_score(lf, rf, lt, st, jt, tt, kt)
        if ts >= 2:
            s = evaluate_move(board, mv, player)
            if s > best_two_win_score:
                best_two_win_score = s
                best_two_win_mv = mv

    if best_two_win_mv is not None:
        return best_two_win_mv

    # Step5 挡对手两步必胜
    best_block_two = None
    best_block_two_score = -1e18

    for mv in valid:
        board[mv] = opponent
        lf, rf, lt, st, jt, tt, kt = quick_evaluate(board, mv, opponent)
        board[mv] = 0

        ts = threat_score(lf, rf, lt, st, jt, tt, kt)
        if ts >= 2:
            s = evaluate_move(board, mv, player)
            if s > best_block_two_score:
                best_block_two_score = s
                best_block_two = mv

    if best_block_two is not None:
        return best_block_two

    # Step6 对手复合冲四
    for mv in valid:
        if is_compound_rush_four(board, mv, opponent):
            return mv

    # Step7 挡对手活三（如果自己没有强攻）
    if not has_strong_attack:
        threats = find_opponent_live_three_blocks(board, opponent)
        if threats:
            blocks = threats[0]
            return choose_best_block(board, player, blocks)

    return None


# ===============================
# MCTS
# ===============================
class MCTSNode:
    def __init__(self, board, parent=None, move=None, player_just_moved=0):
        self.board = board
        self.parent = parent
        self.move = move
        self.player_just_moved = player_just_moved
        self.children = []
        self.wins = 0
        self.visits = 0
        self.untried_moves = get_valid_positions(board)

    def ucb1(self, c=1.41):
        if self.visits == 0:
            return float('inf')
        return (self.wins / self.visits +
                c * np.sqrt(np.log(self.parent.visits) / self.visits))

    def select_child(self):
        return max(self.children, key=lambda ch: ch.ucb1())

    def add_child(self, move, state):
        child = MCTSNode(copy.deepcopy(state),
                         parent=self,
                         move=move,
                         player_just_moved=-self.player_just_moved)
        if move in self.untried_moves:
            self.untried_moves.remove(move)
        self.children.append(child)
        return child

    def update(self, result):
        self.visits += 1
        real = -1 if result == 2 else result
        if self.player_just_moved == real:
            self.wins += 1
        elif result == 0:
            self.wins += 0.5


def rollout(state, player_to_move, max_depth=30):
    cur = player_to_move
    for _ in range(max_depth):
        winner = check_winner(state)
        if winner != 0:
            return winner

        moves = get_valid_positions(state)
        if not moves:
            return check_winner(state)

        scores = []
        for mv in moves:
            s = evaluate_move(state, mv, cur)
            scores.append(max(s, 1.0))

        mv = random.choices(moves, weights=scores, k=1)[0]
        state[mv] = cur
        cur = -cur

    return check_winner(state)


def mcts_best_move(board, player, time_limit=3.0, K=7):
    valid = get_valid_positions(board)
    if not valid:
        return None

    scored = [(evaluate_move(board, mv, player), mv) for mv in valid]
    scored.sort(reverse=True, key=lambda x: x[0])
    K = min(K, len(scored))
    candidates = [mv for s, mv in scored[:K]]

    if scored[0][0] >= 10000:
        return scored[0][1]

    root = MCTSNode(copy.deepcopy(board),
                    parent=None,
                    move=None,
                    player_just_moved=-player)
    root.untried_moves = candidates[:]

    t0 = time.time()
    while time.time() - t0 < time_limit:
        node = root
        state = copy.deepcopy(board)

        while node.untried_moves == [] and node.children:
            node = node.select_child()
            state[node.move] = node.player_just_moved

        if node.untried_moves:
            mv = random.choice(node.untried_moves)
            state[mv] = -node.player_just_moved
            node = node.add_child(mv, state)

        result = rollout(copy.deepcopy(state), -node.player_just_moved)

        while node is not None:
            node.update(result)
            node = node.parent

    if not root.children:
        return random.choice(candidates)

    best_child = max(root.children, key=lambda ch: ch.visits)
    return best_child.move


# ===============================
# 电脑落子
# ===============================
def computer_move(board, player):
    rows, cols = board.shape
    valid = get_valid_positions(board)

    # ---- 黑棋第一手 ----
    if player == 1 and np.count_nonzero(board == 1) == 0 and np.count_nonzero(board == -1) == 0:
        BLACK_OPENING = [(7,7),(7,6),(6,7),(7,8),(8,7)]
        return random.choice(BLACK_OPENING)

    # ---- 白棋第一手 ----
    if player == -1 and np.count_nonzero(board == -1) == 0:
        blacks = list(zip(*np.where(board == 1)))
        if len(blacks) == 1:
            br, bc = blacks[0]
            neighbor = [
                (br+1, bc), (br-1, bc),
                (br, bc+1), (br, bc-1)
            ]
            neighbor = [
                (r,c) for (r,c) in neighbor
                if 0 <= r < rows and 0 <= c < cols and board[r,c] == 0
            ]
            center_candidates = [(7,7), (7,6), (6,7), (8,6), (6,8)]
            center_candidates = [(r,c) for (r,c) in center_candidates if board[r,c] == 0]
            cand = list({*neighbor, *center_candidates})

            best_mv = None
            best_sc = -1e18
            for mv in cand:
                sc = evaluate_move(board, mv, -1)
                if sc > best_sc:
                    best_sc = sc
                    best_mv = mv
            return best_mv

    # ---- 即时决策 ----
    mv = immediate_decision(board, player)
    if mv is not None:
        return mv

    # ---- MCTS ----
    return mcts_best_move(board, player, time_limit=3.0, K=7)


# ===============================
# 游戏主循环
# ===============================
def main(player_is_black=True):
    pg.init()
    surface = draw_board()

    board = np.zeros((15, 15), dtype=int)
    board[np.triu_indices(15, k=1)] = 5
    board = np.flipud(board)

    player_color = 1 if player_is_black else -1
    ai_color = -player_color
    cur_turn = 1
    last_move = None
    game_over = False

    print_text(surface, "Your Turn (Black)" if player_color == 1 else "AI Thinking...")

    while True:
        # AI 回合
        if not game_over and cur_turn == ai_color:
            pg.event.pump()
            print_text(surface, "AI is thinking...", color_red)
            mv = computer_move(board, ai_color)

            if mv is not None:
                board[mv] = ai_color
                if last_move is not None:
                    draw_stone(surface, last_move, -ai_color)
                draw_highlighted_stone(surface, mv, ai_color)
                last_move = mv

                w = check_winner(board)
                if w != 0:
                    print_winner(surface, w)
                    game_over = True
                else:
                    cur_turn = player_color
                    print_text(surface, "Your Turn" if player_color == 1 else "White to play")

        # 玩家事件
        for event in pg.event.get():
            if event.type == pg.QUIT:
                pg.quit()
                return

            if (event.type == pg.MOUSEBUTTONDOWN
                and not game_over
                and cur_turn == player_color):

                idx = click2index(event.pos)
                if idx is not None and board[idx] == 0:
                    board[idx] = player_color
                    if last_move is not None:
                        draw_stone(surface, last_move, ai_color)
                    draw_highlighted_stone(surface, idx, player_color)
                    last_move = idx

                    w = check_winner(board)
                    if w != 0:
                        print_winner(surface, w)
                        game_over = True
                    else:
                        cur_turn = ai_color
                        print_text(surface, "AI Turn", color_red)


if __name__ == "__main__":
    # 随机决定你是不是黑棋（先手）
    player_is_black = random.choice([True, False])
    print("You are BLACK" if player_is_black else "You are WHITE")  # 控制台提示一下
    main(player_is_black=player_is_black)
    # main(player_is_black=True)
