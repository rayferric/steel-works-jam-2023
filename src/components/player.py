import pygame
import os
from pygame.math import Vector2 as Vec2
from time import perf_counter

import core.math
from core.math import BBox
from core.window import Window
from core.camera import Camera
from weapon import Weapon
from math import atan2, pi

from components.map import Map

PIXEL_SIZE = 16


def bfs():
    pass


def lerp(a, b, t):
    return a + (b - a) * t


class Player:
    def __init__(self, follow_camera: Camera, collision_map: Map) -> None:
        self.inertia = 1.0
        self.position = Vec2(0.0, 0.0)
        self.velocity = Vec2(0.0, 0.0)
        self.t_start = perf_counter()
        self.t_stop = perf_counter()
        self.is_jumping = False
        self.is_able_to_jump = False
        self.weapon = Weapon()

        self.follow_camera = follow_camera
        self.collision_map = collision_map
        self.ticks = 0
        self.animidx = 0
        self.images = {
            "jumping": [
                pygame.transform.scale(
                    pygame.image.load("res/player_jump.png"), (PIXEL_SIZE, PIXEL_SIZE)
                )
            ],
            "walking": [
                pygame.transform.scale(
                    pygame.image.load("res/player_r.png"), (PIXEL_SIZE, PIXEL_SIZE)
                ),
                pygame.transform.scale(
                    pygame.image.load("res/player_l.png"), (PIXEL_SIZE, PIXEL_SIZE)
                ),
            ],
            "standing": [
                pygame.transform.scale(
                    pygame.image.load("res/player.png"), (PIXEL_SIZE, PIXEL_SIZE)
                )
            ],
        }
        self.facing = "right"
        # self.hp = 10
        self.is_shot = False
        self.game_mode()
        self.hp = self.max_hp
        # self.acceleration = Vec2(0.0, -10.0)

        self.weapon_rotation = 0

    def rotate_weapon(self, window: Window):
        mouse_pos = Vec2(window.get_input().get_mouse_pos())
        center = Vec2(window._surface.get_width(), window._surface.get_height()) / 2
        vec = mouse_pos - center
        self.weapon_rotation = atan2(vec.y, vec.x) * 180 / pi

    def update(self, window: Window):
        self.rotate_weapon(window)

        y_val = 200
        x_val = 200
        dt = window.get_delta()
        # print(self.hp)
        self.ticks += dt
        if self.ticks > 0.5:  # 1 tick na 16 ms
            self.animidx += 1
            # print(self.animidx)
            self.ticks = 0
        # print(f"self.is_able_to_jump={self.is_able_to_jump}")

        acceleration = Vec2(0.0, y_val)

        if window.get_input().is_action_pressed("right"):
            # if pressed_keys[pygame.K_d]:
            acceleration.x += x_val

        if window.get_input().is_action_pressed("jump"):
            # if pressed_keys[pygame.K_w]:
            if self.is_jumping == False and self.is_able_to_jump == True:
                self.t_start = perf_counter()
                self.is_jumping = True
                self.is_able_to_jump = False
            if self.is_jumping == True:
                self.t_stop = perf_counter()
                if (self.t_stop - self.t_start) <= 0.65:
                    acceleration.y = -y_val
                else:
                    self.is_jumping = False
        else:
            self.is_jumping = False

        if window.get_input().is_action_pressed("left"):
            # if pressed_keys[pygame.K_a]:
            acceleration.x -= x_val

        # print(acceleration)
        if self.is_jumping == False and self.is_able_to_jump == False:
            acceleration.y += 1.25 * y_val

        # if pressed_keys[pygame.K_s]:
        #         acceleration.y += y_val
        fx = 0.45  # 0<f<1
        fy = 0.50  # 0<f<1
        if abs(acceleration.x) > 0:
            self.velocity.x = lerp(
                self.velocity.x,
                self.velocity.x + (acceleration.x * self.inertia * dt),
                fx,
            )
        else:
            self.velocity.x = lerp(self.velocity.x, 0.0, fx)

        if abs(acceleration.y) > 0:
            self.velocity.y = lerp(
                self.velocity.y,
                self.velocity.y + (acceleration.y * self.inertia * dt),
                fy,
            )
        else:
            self.velocity.y = lerp(self.velocity.y, 0.0, fy)

        if self.velocity.x > 0:
            self.facing = "right"
        elif self.velocity.x < 0:
            self.facing = "left"

        max_speed = 10
        if self.velocity.length() > max_speed:
            self.velocity = self.velocity.normalize() * max_speed

        old_position = self.position.copy()
        # self.position = self.position.lerp(self.position + (self.velocity * dt), f)

        # print("PRE", self.velocity, self.position)

        self.position.y = lerp(
            self.position.y, self.position.y + (self.velocity.y * dt), fy
        )

        if self.collision_map.rect_collision(
            bbox=BBox(self.position.x, self.position.y, 1, 1)
        ):
            if old_position.y < self.position.y:
                self.is_able_to_jump = True
            else:
                self.is_jumping = False

            self.position.y = old_position.y
            self.velocity.y = 0

        self.position.x = lerp(
            self.position.x, self.position.x + (self.velocity.x * dt), fx
        )

        if self.collision_map.rect_collision(
            bbox=BBox(self.position.x, self.position.y, 1, 1)
        ):
            # print("x1", self.position.x)
            self.position.x = old_position.x
            # print("x2", self.position.x)
            self.velocity.x = 0

        # print("POST", self.velocity, self.position)

        while item := self.collision_map.take_usable_collision(
            bbox=BBox(self.position.x, self.position.y, 1, 1)
        ):
            self.weapon.add_item(item)

        self.follow_camera.position = (
            core.math.lerp(
                self.follow_camera.position[0],
                (self.position[0] + 0.5) * PIXEL_SIZE,
                5.0 * window.get_delta(),
            ),
            core.math.lerp(
                self.follow_camera.position[1],
                (self.position[1] + 0.5) * PIXEL_SIZE,
                5.0 * window.get_delta(),
            ),
        )

    def draw(self, camera: Camera, uicamera: Camera) -> None:
        surface = pygame.Surface((PIXEL_SIZE * 2, PIXEL_SIZE * 2), pygame.SRCALPHA, 32)
        surface = surface.convert_alpha()
        offset = Vec2(PIXEL_SIZE, PIXEL_SIZE) / 2

        frames = self.images[self.get_state()]
        image = frames[self.animidx % len(frames)]
        if self.facing == "left":
            image = pygame.transform.flip(image, True, False)

        surface.blit(image, offset)

        weapon = self.weapon.get_weapon_as_surface()
        weapon = pygame.transform.rotate(weapon, -self.weapon_rotation)

        surface.blit(weapon, offset + (0, 4))

        camera.blit(
            surface=surface,
            offset=-offset
            + Vec2(
                self.position[0] * PIXEL_SIZE,
                self.position[1] * PIXEL_SIZE,
            ),
        )
        hp_img = pygame.image.load("res/helth.png")
        no_hp_img = pygame.image.load("res/nohelth.png")
        # if self.hp == 10:
        # max_hp = self.hp
        set_y_hp = -160
        for i in range(self.max_hp):
            hp_y = set_y_hp + hp_img.get_height() * i
            if i + 1 <= self.hp:
                uicamera.blit(hp_img, offset=(-320, hp_y))
            else:
                uicamera.blit(no_hp_img, offset=(-320, hp_y))

    def get_state(self):
        if self.is_able_to_jump == False:
            return "jumping"
        if abs(self.velocity.x) > 1e-6:
            return "walking"
        else:
            return "standing"

    def game_mode(self):
        mode = os.environ.get("NAP_GAME_MODE_SELECT_69")
        if mode == "easy":
            self.max_hp = 10
        elif mode == "normal":
            self.max_hp = 5
        else:
            self.max_hp = 3