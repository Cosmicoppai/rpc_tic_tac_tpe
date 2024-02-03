from zero import ZeroServer
from msgspec import Struct
import sqlite3


class Move(Struct):
    token: str
    row: int
    col: int


class RegisterPlayers(Struct):
    token: str
    register: bool = False


class MoveStatus(Struct):
    row: int = 0
    col: int = 0
    status: str = "None"
    move_text: str = ""
    reason: str = ""
    game_status: str = ""


def fetch_player_count():
    conn = sqlite3.connect('players.db')
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) FROM players')
    count = cursor.fetchone()[0]
    conn.close()
    return count


def fetch_player(token: str):
    conn = sqlite3.connect('players.db')
    cursor = conn.cursor()
    cursor.execute('SELECT player_num FROM players WHERE token = ?', (token,))
    player = cursor.fetchone()
    conn.close()
    return player


def add_player(token: str, player: int):
    conn = sqlite3.connect('players.db')
    cursor = conn.cursor()
    cursor.execute('INSERT INTO players (player_num, token) VALUES (?, ?)', (player, token))
    conn.commit()
    conn.close()


def check_token(token: str):
    conn = sqlite3.connect('players.db')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM players WHERE token = ?', (token,))
    player = cursor.fetchone()
    conn.close()
    return player is None


def remove_player(token: str):
    conn = sqlite3.connect('players.db')
    cursor = conn.cursor()
    cursor.execute('DELETE FROM players WHERE token = ?', (token,))
    conn.commit()
    conn.close()


def fetch_currernt_player():
    conn = sqlite3.connect('players.db')
    cursor = conn.cursor()
    cursor.execute('SELECT curr_player from state WHERE id=1')
    player = cursor.fetchone()[0]
    conn.close()
    return player


def change_state(player: int):
    conn = sqlite3.connect('players.db')
    cursor = conn.cursor()
    cursor.execute('UPDATE state SET curr_player = ? WHERE id=1', (player,))
    conn.commit()
    print(fetch_currernt_player())
    conn.close()


app = ZeroServer(port=9000)
_board = [[0, 0, 0], [0, 0, 0], [0, 0, 0]]
LAST_MOVE = MoveStatus()


def gen_token(player: int) -> str:  # function to generate token for player
    return f"player-{player}"  # a simple token to distinguish player


@app.register_rpc
async def register_players(
        client: str) -> RegisterPlayers:  # it'll send true if player successfully registered else false
    players_count = fetch_player_count()
    if players_count < 2:
        player = 1 if players_count == 0 else 2
        token = gen_token(player)
        add_player(token, player)
        return RegisterPlayers(token=token, register=True)
    return RegisterPlayers(token="", register=False)


@app.register_rpc
async def move(player_move: dict) -> MoveStatus:  # function to receive move from client
    global LAST_MOVE
    player_move = Move(**player_move)
    players_count = fetch_player_count()
    if players_count != 2:
        return MoveStatus(status="Failed", reason="Waiting for another player to join")
    elif check_token(player_move.token):
        return MoveStatus(status="Failed", reason="Invalid token")

    CURR_PLAYER_NO = fetch_currernt_player()
    move_played_by = fetch_player(player_move.token)[0]

    if move_played_by == CURR_PLAYER_NO:  # check if move is initiated by current player
        row, col = player_move.row, player_move.col
        _move_text = make_move(row, col, CURR_PLAYER_NO)  # make move
        winner = check_for_winner()
        _last_move = MoveStatus(row=player_move.row, col=player_move.col, status="Success", move_text=_move_text,
                               game_status=winner if winner else "")
        LAST_MOVE = _last_move
        if winner:
            clean_up()
        return _last_move
    else:
        return MoveStatus(status="Failed", reason="Not your turn")


@app.register_rpc
async def fetch_data() -> MoveStatus:
    global LAST_MOVE
    return LAST_MOVE


@app.register_rpc
async def reset() -> str:
    global _board
    global CURR_PLAYER
    _board = [[0, 0, 0], [0, 0, 0], [0, 0, 0]]
    CURR_PLAYER = 1
    return None


@app.register_rpc
async def quit_game(token: str) -> str:
    remove_player(token)
    return None


def make_move(row: int, col: int, curr_player: int) -> str:
    _move_text = None
    if curr_player == 1:
        _move_text = "X"
        _board[row][col] = _move_text
        curr_player = 2
    else:
        _move_text = "O"
        _board[row][col] = _move_text
        curr_player = 1

    change_state(curr_player)

    return _move_text


def check_for_winner() -> str:
    winner = None

    # Check rows
    for row in _board:
        if row.count(row[0]) == len(row) and row[0] != 0:
            winner = row[0]
            break

    # Check columns
    for col in range(len(_board)):
        if _board[0][col] == _board[1][col] == _board[2][col] and _board[0][col] != 0:
            winner = _board[0][col]
            break

    # Check diagonals
    if _board[0][0] == _board[1][1] == _board[2][2] and _board[0][0] != 0:
        winner = _board[0][0]
    elif _board[0][2] == _board[1][1] == _board[2][0] and _board[0][2] != 0:
        winner = _board[0][2]

    if all([all(row) for row in _board]) and winner is None:
        winner = "tie"

    return winner


def clean_up():
    LAST_MOVE = MoveStatus()

def start_server():
    app.run(workers=1)


if __name__ == "__main__":
    conn = sqlite3.connect('players.db')
    cursor = conn.cursor()

    delete_table_query = '''
    DROP TABLE IF EXISTS players;
    '''
    cursor.execute(delete_table_query)

    create_table_query = '''
    CREATE TABLE IF NOT EXISTS players (
        player_num INTEGER PRIMARY KEY,
        token TEXT UNIQUE NOT NULL
    );
    '''

    cursor.execute(create_table_query)

    create_table_query = '''
    CREATE TABLE IF NOT EXISTS state (
        id INTEGER PRIMARY KEY,
        curr_player INTEGER NOT NULL DEFAULT 1
    );
    '''
    cursor.execute(create_table_query)

    create_table_query = '''
    INSERT INTO state (id, curr_player) VALUES (1, 1) ON CONFLICT(id) DO UPDATE SET curr_player=1;
    '''
    cursor.execute(create_table_query)

    conn.commit()
    conn.close()

    start_server()
