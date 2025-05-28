% Wumpus World Knowledge Base

% Facts about the cave configuration (4x4 grid example)
% cell(X, Y): Represents a cell at position (X,Y)
cell(1,1). cell(1,2). cell(1,3). cell(1,4).
cell(2,1). cell(2,2). cell(2,3). cell(2,4).
cell(3,1). cell(3,2). cell(3,3). cell(3,4).
cell(4,1). cell(4,2). cell(4,3). cell(4,4).

% Adjacent cells (for movement)
adjacent(X, Y, X1, Y) :- X1 is X+1, cell(X1, Y). % Right
adjacent(X, Y, X1, Y) :- X1 is X-1, cell(X1, Y). % Left
adjacent(X, Y, X, Y1) :- Y1 is Y+1, cell(X, Y1). % Up
adjacent(X, Y, X, Y1) :- Y1 is Y-1, cell(X, Y1). % Down

% Initial percepts (these would change as the agent moves)
% stench(X,Y): Wumpus is in an adjacent cell
% breeze(X,Y): Pit is in an adjacent cell
% glitter(X,Y): Gold is in this cell
% scream: Wumpus has been shot (global)
% bump: Agent hit a wall (instant percept)

% Example initial percepts for a configuration
stench(1,2). % Wumpus is adjacent to (1,2)
breeze(2,1).  % Pit is adjacent to (2,1)
glitter(3,3). % Gold is at (3,3)

% Rules to infer dangers
wumpus(X,Y) :-
    adjacent(X,Y,WX,WY),
    stench(WX,WY),
    \+ confirmed_safe(WX,WY),
    \+ killed_wumpus.

pit(X,Y) :-
    adjacent(X,Y,PX,PY),
    breeze(PX,PY),
    \+ confirmed_safe(PX,PY).

% Rules for safe cells
confirmed_safe(X,Y) :-
    visited(X,Y),
    \+ wumpus(X,Y),
    \+ pit(X,Y).

% Agent's knowledge (dynamic predicates)
:- dynamic visited/2.
:- dynamic has_gold/0.
:- dynamic has_arrow/1.
:- dynamic facing/1.
:- dynamic current_pos/2.

% Initial agent state
has_arrow(true).
facing(east).
current_pos(1,1).

% Movement rules
move_forward :-
    current_pos(X,Y),
    facing(Dir),
    (Dir = east -> X1 is X+1, Y1 = Y;
     Dir = west -> X1 is X-1, Y1 = Y;
     Dir = north -> Y1 is Y+1, X1 = X;
     Dir = south -> Y1 is Y-1, X1 = X),
    (cell(X1,Y1) ->
        retract(current_pos(X,Y)),
        asserta(current_pos(X1,Y1)),
        asserta(visited(X1,Y1)),
        format('Moved to (~w,~w)~n', [X1,Y1]);
     format('Bump! Cannot move ~w from (~w,~w)~n', [Dir,X,Y])).

turn_left :-
    facing(Dir),
    (Dir = east -> NewDir = north;
     Dir = north -> NewDir = west;
     Dir = west -> NewDir = south;
     Dir = south -> NewDir = east),
    retract(facing(Dir)),
    asserta(facing(NewDir)),
    format('Turned left, now facing ~w~n', [NewDir]).

turn_right :-
    facing(Dir),
    (Dir = east -> NewDir = south;
     Dir = south -> NewDir = west;
     Dir = west -> NewDir = north;
     Dir = north -> NewDir = east),
    retract(facing(Dir)),
    asserta(facing(NewDir)),
    format('Turned right, now facing ~w~n', [NewDir]).

% Action rules
grab_gold :-
    current_pos(X,Y),
    glitter(X,Y),
    \+ has_gold,
    asserta(has_gold),
    retract(glitter(X,Y)),
    format('Picked up the gold at (~w,~w)~n', [X,Y]).

shoot_arrow :-
    has_arrow(true),
    retract(has_arrow(true)),
    asserta(has_arrow(false)),
    current_pos(X,Y),
    facing(Dir),
    (Dir = east -> find_wumpus(X,Y,1,0);
     Dir = west -> find_wumpus(X,Y,-1,0);
     Dir = north -> find_wumpus(X,Y,0,1);
     Dir = south -> find_wumpus(X,Y,0,-1)),
    format('Arrow shot!~n').

find_wumpus(X,Y,DX,DY) :-
    X1 is X + DX,
    Y1 is Y + DY,
    (wumpus(X1,Y1) ->
        retract(wumpus(X1,Y1)),
        asserta(killed_wumpus),
        format('You killed the Wumpus at (~w,~w)!~n', [X1,Y1]);
     cell(X1,Y1) -> find_wumpus(X1,Y1,DX,DY);
     true).

climb_out :-
    current_pos(1,1),
    (has_gold -> format('You climbed out with the gold! You win!~n');
     format('You climbed out without the gold.~n')).

% Perception rules
perceive :-
    current_pos(X,Y),
    format('At position (~w,~w) you perceive:~n', [X,Y]),
    (stench(X,Y) -> format(' - Stench~n'); true),
    (breeze(X,Y) -> format(' - Breeze~n'); true),
    (glitter(X,Y) -> format(' - Glitter~n'); true),
    (wumpus(X,Y) -> format('You are eaten by the Wumpus! Game over.~n', []), halt;
     pit(X,Y) -> format('You fell into a pit! Game over.~n', []), halt;
     true).
