from __future__ import annotations

from dataclasses import replace

from . import events as ev
from .actions import Action, Attack, Decline, Move, RunAground, TransferFlag
from .board import BASE, adjacent, in_bounds, neighbours, wall_blocks
from .combat import Fate, resolve
from .state import FlagLoc, GameState, Piece
from .types import Player, PieceType

T = PieceType

# Pieces that survive moving adjacent to an enemy Mine.
MINE_EXEMPT = {T.MINE_SWEEPER, T.MINE_LAYER, T.FLYING_BOAT}
# Pieces that survive moving adjacent to an enemy Mine Layer. The Destroyer's
# exemption is a documented house ruling: it is the only piece able to sink a
# Mine Layer, which would be impossible if adjacency killed it first.
MINE_LAYER_EXEMPT = {
    T.MINE_SWEEPER,
    T.SUBMARINE,
    T.FLYING_BOAT,
    T.MINE_LAYER,
    T.DESTROYER,
}


class IllegalAction(Exception):
    pass


def apply_action(state: GameState, action: Action) -> tuple[GameState, list]:
    if state.winner is not None:
        raise IllegalAction("game is over")

    obligated = _pieces_obliged_to_leave_base(state)
    if obligated:
        ok = (
            isinstance(action, Move) and action.piece_id in obligated
        ) or (isinstance(action, RunAground) and action.piece_id in obligated)
        if not ok:
            raise IllegalAction("the ship on the Base must be moved off first")

    if isinstance(action, Move):
        return _apply_move(state, action)
    if isinstance(action, Attack):
        return _apply_attack(state, action)
    if isinstance(action, Decline):
        return _apply_decline(state, action)
    if isinstance(action, TransferFlag):
        return _apply_transfer(state, action)
    if isinstance(action, RunAground):
        return _apply_run_aground(state, action)
    raise IllegalAction(f"unsupported action {action!r}")


def _pieces_obliged_to_leave_base(state: GameState) -> set[str]:
    """Ships standing on a Base at their owner's turn must sail off it."""
    return {
        p.id
        for p in state.pieces.values()
        if p.owner is state.to_move and p.square in (BASE[Player.A], BASE[Player.B])
    }


# --- movement ---------------------------------------------------------------


def _require_own_live_piece(state: GameState, piece_id: str) -> Piece:
    piece = state.pieces.get(piece_id)
    if piece is None or piece.square is None:
        raise IllegalAction("no such piece on the board")
    if piece.owner is not state.to_move:
        raise IllegalAction("not this player's piece")
    return piece


def _validate_move_geometry(state: GameState, piece: Piece, to) -> bool:
    """Returns True when the move is a Flying Boat two-square mine jump."""
    if not in_bounds(to):
        raise IllegalAction("destination off the board")
    if state.piece_at(to) is not None:
        raise IllegalAction("destination occupied")

    frm = piece.square
    dc, dr = to[0] - frm[0], to[1] - frm[1]
    if abs(dc) + abs(dr) == 1:
        return False
    if (
        piece.type is T.FLYING_BOAT
        and {abs(dc), abs(dr)} == {0, 2}
    ):
        over = (frm[0] + dc // 2, frm[1] + dr // 2)
        hopped = state.piece_at(over)
        if hopped is None or hopped.type is not T.MINE:
            raise IllegalAction("Flying Boat may only jump over a Mine")
        return True
    raise IllegalAction("pieces move one square orthogonally")


def _crossed_wall_edges(frm, to) -> list[tuple]:
    """Edges traversed by the move (one, or two for a Flying Boat jump)."""
    step = ((to[0] - frm[0]) and (1 if to[0] > frm[0] else -1),
            (to[1] - frm[1]) and (1 if to[1] > frm[1] else -1))
    edges, cur = [], frm
    while cur != to:
        nxt = (cur[0] + step[0], cur[1] + step[1])
        edges.append((cur, nxt))
        cur = nxt
    return [e for e in edges if wall_blocks(*e)]


def _validate_base_entry(state: GameState, piece: Piece, to) -> None:
    for player in Player:
        if to != BASE[player]:
            continue
        if state.mode == "capture_base":
            if player is piece.owner:
                raise IllegalAction("no ship is allowed on its own Base")
            return  # entering the enemy base: the winning move
        if player is piece.owner:
            if not piece.carrying:
                raise IllegalAction("no ship is allowed on the Base except to leave a Flag")
            if piece.owner.opponent in piece.carrying:
                _require_own_flag_home_side(state, piece)
        else:
            flag_here = any(loc.square == to for loc in state.flags.values())
            if not flag_here:
                raise IllegalAction("no ship is allowed on the Base except to capture")


def _require_own_flag_home_side(state: GameState, piece: Piece) -> None:
    """Enemy flag may only be deposited if your own flag is in your possession
    and on your side of the board."""
    own = piece.owner
    loc = state.flags[own]
    if own in piece.carrying:
        return  # arriving with both flags
    if loc.carrier is not None:
        carrier = state.pieces[loc.carrier]
        if carrier.owner is own and _on_own_side(own, carrier.square):
            return
        raise IllegalAction("own Flag is not in possession on your side of the board")
    if loc.square == BASE[own]:
        return
    raise IllegalAction("own Flag is not in possession on your side of the board")


def _on_own_side(player: Player, square) -> bool:
    return square[1] <= 5 if player is Player.A else square[1] >= 6


def _validate_flag_square_entry(state: GameState, piece: Piece, to) -> None:
    for loc in state.flags.values():
        if loc.square == to and loc.sweeper_only and piece.type is not T.MINE_SWEEPER:
            raise IllegalAction("a Flag lost to a mine can be recovered only by a Mine Sweeper")


def _apply_move(state: GameState, action: Move) -> tuple[GameState, list]:
    piece = _require_own_live_piece(state, action.piece_id)
    if piece.type is T.MINE:
        raise IllegalAction("Mines remain stationary throughout the game")

    is_jump = _validate_move_geometry(state, piece, action.to)
    walls = _crossed_wall_edges(piece.square, action.to)
    if walls and piece.type is not T.FLYING_BOAT:
        raise IllegalAction("the Harbour Wall blocks everything but the Flying Boat")
    _validate_base_entry(state, piece, action.to)
    _validate_flag_square_entry(state, piece, action.to)

    events: list = [ev.Moved(piece.id, piece.square, action.to)]
    pieces = dict(state.pieces)
    knowledge = {p: dict(k) for p, k in state.knowledge.items()}
    flags = dict(state.flags)
    moved = replace(piece, square=action.to)
    pieces[piece.id] = moved

    opponent = piece.owner.opponent
    if walls:
        events.append(ev.WallCrossed(piece.id))
        knowledge[opponent][piece.id] = T.FLYING_BOAT
    if is_jump:
        # A two-square hop is publicly a Flying Boat move.
        knowledge[opponent][piece.id] = T.FLYING_BOAT

    # Passive hazards: resolved on movement, before any pickup or capture.
    died = _resolve_passive_hazards(pieces, knowledge, flags, moved, events)

    new_declines: set[frozenset[str]] = set()
    if not died:
        _resolve_flag_arrival(state, pieces, flags, pieces[piece.id], events)
        died = _resolve_move_declaration(
            state, pieces, knowledge, flags, piece, action, events, new_declines
        )
    elif action.attack is not None:
        pass  # blown up "whether it attacks or not" — the declaration is moot

    declined = frozenset(
        pair for pair in state.declined
        if piece.id not in pair and all(pieces[p].square is not None for p in pair)
    ) | frozenset(new_declines)

    new = replace(
        state,
        pieces=pieces,
        flags=flags,
        knowledge=knowledge,
        declined=declined,
        transfer_window=frozenset(
            _window_kept_from(state, state.to_move)
            | set(_transfer_window_after_move(pieces, flags, piece.id, died))
        ),
        to_move=state.to_move.opponent,
    )
    return _finish_turn(new, events)


def _resolve_passive_hazards(pieces, knowledge, flags, moved: Piece, events) -> bool:
    """Mine / Mine Layer adjacency kills. Returns True if the mover died."""
    hazards = []
    for other in pieces.values():
        if other.owner is moved.owner or other.square is None:
            continue
        if not adjacent(moved.square, other.square):
            continue
        if other.type is T.MINE and moved.type not in MINE_EXEMPT:
            hazards.append(other)
        elif other.type is T.MINE_LAYER and moved.type not in MINE_LAYER_EXEMPT:
            hazards.append(other)
    if not hazards:
        return False

    for hazard in hazards:
        events.append(ev.PassiveKill(moved.id, hazard.id))
        knowledge[moved.owner][hazard.id] = hazard.type

    square = moved.square
    pieces[moved.id] = replace(moved, square=None, carrying=frozenset())
    for flag_owner in moved.carrying:
        sweeper_only = any(h.type is T.MINE for h in hazards)
        flags[flag_owner] = FlagLoc(square=square, sweeper_only=sweeper_only)
        events.append(ev.FlagDropped(flag_owner, square, sweeper_only))
    return True


def _resolve_flag_arrival(state, pieces, flags, moved: Piece, events) -> None:
    """Pick up a loose flag, capture from a base, or deposit on our own base."""
    carrying = set(moved.carrying)

    for flag_owner, loc in list(flags.items()):
        if loc.square == moved.square:
            if moved.square == BASE[moved.owner] and flag_owner is moved.owner:
                continue  # our own flag sitting on our own base is not picked up
            carrying.add(flag_owner)
            flags[flag_owner] = FlagLoc(carrier=moved.id)
            kind = ev.FlagCaptured if moved.square == BASE[flag_owner] else ev.FlagPickedUp
            events.append(kind(flag_owner, moved.id))

    if moved.square == BASE[moved.owner] and carrying:
        for flag_owner in sorted(carrying, key=lambda p: p.value):
            flags[flag_owner] = FlagLoc(square=moved.square)
            events.append(ev.FlagDeposited(flag_owner, moved.owner))
        carrying.clear()

    pieces[moved.id] = replace(moved, carrying=frozenset(carrying))


def _window_kept_from(state: GameState, actor: Player) -> set[tuple[str, str]]:
    """Window entries belong to the player whose move created them; an
    opponent's action must not expire them."""
    return {
        (giver, receiver)
        for giver, receiver in state.transfer_window
        if state.pieces[giver].owner is not actor
    }


def _transfer_window_after_move(pieces, flags, moved_id: str, died: bool) -> frozenset:
    """Transfers must happen on the move immediately after the move that set
    up the adjacency, so only adjacencies created by this move count."""
    if died:
        return frozenset()
    moved = pieces[moved_id]
    window = set()
    for other in pieces.values():
        if other.owner is not moved.owner or other.square is None or other.id == moved.id:
            continue
        if not adjacent(moved.square, other.square):
            continue
        if moved.carrying and other.type is not T.MINE:
            window.add((moved.id, other.id))
        if other.carrying and moved.type is not T.MINE:
            window.add((other.id, moved.id))
    return frozenset(window)


# --- attacks ----------------------------------------------------------------


def _attack_bar_reason(state: GameState, attacker: Piece, defender: Piece) -> str | None:
    if attacker.type in (T.MINE_LAYER, T.MINE):
        return f"a {attacker.type.value} may never attack"
    if defender.owner is attacker.owner:
        return "cannot attack your own piece"
    if attacker.carrying and defender.carrying:
        return "a ship carrying a Flag cannot attack the ship carrying the other one"
    return None


def _resolve_move_declaration(
    state, pieces, knowledge, flags, piece: Piece, action: Move, events, new_declines
) -> bool:
    """Handle the simultaneous "Attack!" / "No Attack!" declaration for the
    back-to-back contacts this move created. Returns True if the mover sank."""
    moved = pieces[piece.id]
    old_square = piece.square
    contacts = [
        other
        for other in pieces.values()
        if other.owner is not moved.owner
        and other.square is not None
        and adjacent(moved.square, other.square)
        and not adjacent(old_square, other.square)
    ]
    attackable = [
        c for c in contacts if _attack_bar_reason(state, moved, c) is None
    ]

    if action.attack is None:
        if state.mode == "capture_base" and attackable:
            raise IllegalAction("in the short game an attack must be declared on contact")
        for other in attackable:
            new_declines.add(frozenset({moved.id, other.id}))
            events.append(ev.Declined(moved.id, other.id))
        return False

    target = next((c for c in contacts if c.square == action.attack), None)
    if target is None:
        raise IllegalAction("declared attack must target a piece this move came back-to-back with")
    reason = _attack_bar_reason(state, moved, target)
    if reason is not None:
        raise IllegalAction(reason)
    for other in attackable:
        if other.id != target.id:
            new_declines.add(frozenset({moved.id, other.id}))
            events.append(ev.Declined(moved.id, other.id))
    return _resolve_combat(pieces, knowledge, flags, moved, target, events)


def _resolve_combat(pieces, knowledge, flags, attacker: Piece, defender: Piece, events) -> bool:
    """Resolve a declared attack. Returns True if the attacker sank."""
    attacker_fate, defender_fate = resolve(attacker.type, defender.type)
    events.append(
        ev.Combat(
            attacker.id,
            defender.id,
            attacker.type,
            defender.type,
            attacker_fate,
            defender_fate,
        )
    )
    # "Immediately an attack is made both players show the pieces concerned."
    knowledge[attacker.owner][defender.id] = defender.type
    knowledge[defender.owner][attacker.id] = attacker.type

    for piece, fate, other, other_fate in (
        (attacker, attacker_fate, defender, defender_fate),
        (defender, defender_fate, attacker, attacker_fate),
    ):
        if fate is not Fate.SUNK:
            continue
        pieces[piece.id] = replace(piece, square=None, carrying=frozenset())
        for flag_owner in piece.carrying:
            if other_fate is Fate.SUNK:
                # Equal-value duel with a carrier: the flag drops where the
                # escort stood, prize of the first ship of either side.
                flags[flag_owner] = FlagLoc(square=piece.square)
                events.append(ev.FlagDropped(flag_owner, piece.square, False))
            else:
                survivor = pieces[other.id]
                pieces[other.id] = replace(
                    survivor, carrying=survivor.carrying | {flag_owner}
                )
                flags[flag_owner] = FlagLoc(carrier=other.id)
                events.append(ev.FlagCaptured(flag_owner, other.id))
    return attacker_fate is Fate.SUNK


def _apply_attack(state: GameState, action: Attack) -> tuple[GameState, list]:
    attacker = _require_own_live_piece(state, action.piece_id)
    defender = state.piece_at(action.target_square)
    if defender is None or defender.square is None:
        raise IllegalAction("no piece on the target square")
    if not adjacent(attacker.square, defender.square):
        raise IllegalAction("pieces may only attack when back to back")
    if frozenset({attacker.id, defender.id}) in state.declined:
        raise IllegalAction("this pair was declined; a piece must move first")
    reason = _attack_bar_reason(state, attacker, defender)
    if reason is not None:
        raise IllegalAction(reason)

    events: list = []
    pieces = dict(state.pieces)
    knowledge = {p: dict(k) for p, k in state.knowledge.items()}
    flags = dict(state.flags)
    _resolve_combat(pieces, knowledge, flags, attacker, defender, events)

    declined = frozenset(
        pair
        for pair in state.declined
        if all(pieces[p].square is not None for p in pair)
    )
    new = replace(
        state,
        pieces=pieces,
        flags=flags,
        knowledge=knowledge,
        declined=declined,
        transfer_window=frozenset(_window_kept_from(state, state.to_move)),
        to_move=state.to_move.opponent,
    )
    return _finish_turn(new, events)


def _apply_decline(state: GameState, action: Decline) -> tuple[GameState, list]:
    if state.mode == "capture_base":
        raise IllegalAction("attacks are compulsory in the short game")
    attacker = _require_own_live_piece(state, action.piece_id)
    defender = state.piece_at(action.target_square)
    if defender is None:
        raise IllegalAction("no piece on the target square")
    if not adjacent(attacker.square, defender.square):
        raise IllegalAction("pieces may only decline when back to back")
    if frozenset({attacker.id, defender.id}) in state.declined:
        raise IllegalAction("this pair is already declined")
    reason = _attack_bar_reason(state, attacker, defender)
    if reason is not None:
        raise IllegalAction(reason)

    new = replace(
        state,
        declined=state.declined | {frozenset({attacker.id, defender.id})},
        transfer_window=frozenset(_window_kept_from(state, state.to_move)),
        to_move=state.to_move.opponent,
    )
    return _finish_turn(new, [ev.Declined(attacker.id, defender.id)])


# --- flag transfer and running aground --------------------------------------


def _apply_transfer(state: GameState, action: TransferFlag) -> tuple[GameState, list]:
    giver = _require_own_live_piece(state, action.from_piece)
    if (action.from_piece, action.to_piece) not in state.transfer_window:
        raise IllegalAction(
            "a transfer must happen on the move immediately after getting into position"
        )
    receiver = state.pieces.get(action.to_piece)
    if receiver is None or receiver.square is None or receiver.owner is not giver.owner:
        raise IllegalAction("no friendly vessel to transfer to")
    if not giver.carrying:
        raise IllegalAction("this piece carries no flag")
    if not adjacent(giver.square, receiver.square):
        raise IllegalAction("the receiving vessel is no longer alongside")

    pieces = dict(state.pieces)
    flags = dict(state.flags)
    events: list = []
    pieces[giver.id] = replace(giver, carrying=frozenset())
    pieces[receiver.id] = replace(receiver, carrying=receiver.carrying | giver.carrying)
    for flag_owner in sorted(giver.carrying, key=lambda p: p.value):
        flags[flag_owner] = FlagLoc(carrier=receiver.id)
        events.append(ev.FlagTransferred(flag_owner, giver.id, receiver.id))

    new = replace(
        state,
        pieces=pieces,
        flags=flags,
        transfer_window=frozenset(_window_kept_from(state, state.to_move)),
        to_move=state.to_move.opponent,
    )
    return _finish_turn(new, events)


def _apply_run_aground(state: GameState, action: RunAground) -> tuple[GameState, list]:
    piece = _require_own_live_piece(state, action.piece_id)
    if piece.square not in (BASE[Player.A], BASE[Player.B]):
        raise IllegalAction("only a ship stuck on a Base can run aground")
    if any(_move_would_be_legal(state, piece, to) for to in _candidate_squares(piece)):
        raise IllegalAction("the ship can still sail off the Base")

    pieces = dict(state.pieces)
    flags = dict(state.flags)
    events: list = [ev.RanAground(piece.id)]
    base_square = piece.square
    pieces[piece.id] = replace(piece, square=None, carrying=frozenset())
    for flag_owner in sorted(piece.carrying, key=lambda p: p.value):
        flags[flag_owner] = FlagLoc(square=base_square)
        events.append(ev.FlagDropped(flag_owner, base_square, False))

    declined = frozenset(pair for pair in state.declined if piece.id not in pair)
    new = replace(
        state,
        pieces=pieces,
        flags=flags,
        declined=declined,
        transfer_window=frozenset(_window_kept_from(state, state.to_move)),
        to_move=state.to_move.opponent,
    )
    return _finish_turn(new, events)


# --- legal-action existence (for run-aground and hem-in checks) -------------


def _candidate_squares(piece: Piece) -> list:
    squares = neighbours(piece.square)
    if piece.type is T.FLYING_BOAT:
        col, row = piece.square
        squares += [
            sq
            for sq in [(col + 2, row), (col - 2, row), (col, row + 2), (col, row - 2)]
            if in_bounds(sq)
        ]
    return squares


def _move_would_be_legal(state: GameState, piece: Piece, to) -> bool:
    if piece.type is T.MINE:
        return False
    try:
        _validate_move_geometry(state, piece, to)
        if _crossed_wall_edges(piece.square, to) and piece.type is not T.FLYING_BOAT:
            return False
        _validate_base_entry(state, piece, to)
        _validate_flag_square_entry(state, piece, to)
    except IllegalAction:
        return False
    return True


def _has_any_legal_action(state: GameState) -> bool:
    obligated = _pieces_obliged_to_leave_base(state)
    if obligated:
        return True  # move off, or failing that run aground — always playable
    for piece in state.pieces.values():
        if piece.owner is not state.to_move or piece.square is None:
            continue
        if any(_move_would_be_legal(state, piece, to) for to in _candidate_squares(piece)):
            return True
        for other in state.pieces.values():
            if (
                other.owner is piece.owner
                or other.square is None
                or not adjacent(piece.square, other.square)
            ):
                continue
            if frozenset({piece.id, other.id}) in state.declined:
                continue
            if _attack_bar_reason(state, piece, other) is None:
                return True
    for giver_id, receiver_id in state.transfer_window:
        giver = state.pieces[giver_id]
        receiver = state.pieces[receiver_id]
        if (
            giver.owner is state.to_move
            and giver.square is not None
            and receiver.square is not None
            and giver.carrying
            and adjacent(giver.square, receiver.square)
        ):
            return True
    return False


# --- legal action generation ------------------------------------------------


def _would_die_at(state: GameState, piece: Piece, to) -> bool:
    for other in state.pieces.values():
        if other.owner is piece.owner or other.square is None or other.id == piece.id:
            continue
        if not adjacent(to, other.square):
            continue
        if other.type is T.MINE and piece.type not in MINE_EXEMPT:
            return True
        if other.type is T.MINE_LAYER and piece.type not in MINE_LAYER_EXEMPT:
            return True
    return False


def _move_actions_for(state: GameState, piece: Piece) -> list[Action]:
    actions: list[Action] = []
    for to in _candidate_squares(piece):
        if not _move_would_be_legal(state, piece, to):
            continue
        if _would_die_at(state, piece, to):
            actions.append(Move(piece.id, to))  # the declaration is moot
            continue
        contacts = [
            other
            for other in state.pieces.values()
            if other.owner is not piece.owner
            and other.square is not None
            and adjacent(to, other.square)
            and not adjacent(piece.square, other.square)
        ]
        attackable = [
            c for c in contacts if _attack_bar_reason(state, piece, c) is None
        ]
        for target in attackable:
            actions.append(Move(piece.id, to, attack=target.square))
        if not (state.mode == "capture_base" and attackable):
            actions.append(Move(piece.id, to))
    return actions


def legal_actions(state: GameState) -> list[Action]:
    if state.winner is not None:
        return []

    obligated = _pieces_obliged_to_leave_base(state)
    if obligated:
        moves: list[Action] = []
        for pid in sorted(obligated):
            moves += _move_actions_for(state, state.pieces[pid])
        return moves or [RunAground(pid) for pid in sorted(obligated)]

    actions: list[Action] = []
    for piece in state.pieces.values():
        if piece.owner is not state.to_move or piece.square is None:
            continue
        if piece.type is not T.MINE:
            actions += _move_actions_for(state, piece)
        for other in state.pieces.values():
            if (
                other.owner is piece.owner
                or other.square is None
                or not adjacent(piece.square, other.square)
            ):
                continue
            if frozenset({piece.id, other.id}) in state.declined:
                continue
            if _attack_bar_reason(state, piece, other) is None:
                actions.append(Attack(piece.id, other.square))
                if state.mode != "capture_base":
                    actions.append(Decline(piece.id, other.square))
    for giver_id, receiver_id in sorted(state.transfer_window):
        giver = state.pieces[giver_id]
        receiver = state.pieces[receiver_id]
        if (
            giver.owner is state.to_move
            and giver.square is not None
            and receiver.square is not None
            and giver.carrying
            and adjacent(giver.square, receiver.square)
        ):
            actions.append(TransferFlag(giver_id, receiver_id))
    return actions


# --- end-of-turn bookkeeping ------------------------------------------------


def _finish_turn(state: GameState, events: list) -> tuple[GameState, list]:
    winner = _check_winner(state)
    if winner is None and not _has_any_legal_action(state):
        # "A player also wins if he so hems in his opponent's pieces that his
        # opponent cannot move ... The winning player, however, must have his
        # own Flag on his own Base, otherwise the game is drawn."
        hemmer = state.to_move.opponent
        if state.mode == "capture_base":
            winner = hemmer
        elif state.flags[hemmer].square == BASE[hemmer]:
            winner = hemmer
        else:
            winner = "draw"
    if winner is not None:
        state = replace(state, winner=winner)
        events.append(ev.GameOver(winner))
    return state, events


def _check_winner(state: GameState):
    if state.mode == "capture_base":
        for player in Player:
            enemy_base = BASE[player.opponent]
            occupant = state.piece_at(enemy_base)
            if occupant is not None and occupant.owner is player:
                return player
        return None
    for player in Player:
        if all(loc.square == BASE[player] for loc in state.flags.values()):
            return player
    return None
