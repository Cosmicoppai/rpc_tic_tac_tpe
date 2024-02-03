if __name__ == "__main__":

    import tkinter as tk
    from tkinter import messagebox
    from zero import ZeroClient
    from msgspec import Struct

    ZERO_CLIENT = ZeroClient("localhost", 9000)
    _player_token = None


    class Move(Struct):
        token: str
        row: int
        col: int


    class MoveStatus(Struct):
        row: int = 0
        col: int = 0
        status: str = "None"
        move_text: str = ""
        reason: str = ""
        game_status: str = ""


    class RegisterPlayers(Struct):
        token: str
        register: bool = False


    def send_move(move: Move):
        return ZERO_CLIENT.call("move", move, return_type=MoveStatus)


    def register_players():
        global _player_token
        resp = ZERO_CLIENT.call("register_players", ZERO_CLIENT.__str__(), return_type=RegisterPlayers)
        if resp.register:
            _player_token = resp.token
            return True
        else:
            show_error("Lobby is full")
            return False


    def reset():
        ZERO_CLIENT.call('reset', None)
        fetch_data()


    def quit_game():
        ZERO_CLIENT.call('quit_game', _player_token)
        ZERO_CLIENT.close()


    window = tk.Tk()
    window.title("Tic Tac Toe")


    # Create board
    def create_board():
        for i in range(3):
            for j in range(3):
                button = tk.Button(window, text="", font=("Arial", 50), height=2, width=6, bg="lightblue",
                                   command=lambda row=i, col=j: handle_click(row, col))
                button.grid(row=i, column=j, sticky="nsew")

    player_registered = register_players()
    if player_registered:
        create_board()


    # Handle button clicks
    def handle_click(row, col):
        move_resp = send_move(Move(token=_player_token, row=row, col=col))
        update_state(move_resp)

    def update_state(move_resp):
        if move_resp.status.lower() == "success":
            button = window.grid_slaves(row=move_resp.row, column=move_resp.col)[0]
            button.config(text=move_resp.move_text)
            if move_resp.game_status:
                declare_winner(move_resp.game_status)
        elif move_resp.status.lower() == "none":
            ...
        else:
            show_error(move_resp.reason)

    def fetch_data():
        move_resp = ZERO_CLIENT.call('fetch_data', None, return_type=MoveStatus)
        update_state(move_resp)
        if not move_resp.game_status: # stop fetching data if game is over
            window.after(500, fetch_data)


    def show_error(err: str):
        messagebox.showerror("Error", err)


    # Declare the winner and ask to restart the game
    def declare_winner(winner):
        if winner == "tie":
            message = "It's a tie!"
        else:
            message = f"Player {winner} wins!"

        answer = messagebox.askyesno("Game Over", message + " Do you want to restart the game?")

        if answer:
            reset()
            for i in range(3):
                for j in range(3):
                    button = window.grid_slaves(row=i, column=j)[0]
                    button.config(text="")
        else:
            quit_game()
            window.quit()

    if player_registered:
        fetch_data()

    window.mainloop()
