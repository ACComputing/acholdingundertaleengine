import base64
import io
import math
import random
import sys
import time

import pygame
from aigptundertale_ost_data import OST_AUDIO_B64, OST_FORMAT, OST_TITLE

pygame.init()

# Window + timing: Undertale battle logic runs at ~30 Hz; we render at 60 FPS and scale
# per-frame motion so real-time speed matches the original.
DISPLAY_FPS = 60
UNDERTALE_FPS = 30
UT_SPEED = UNDERTALE_FPS / DISPLAY_FPS

WIDTH, HEIGHT = 800, 600
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("AC'S UNDERTALE SANS FIGHT")
clock = pygame.time.Clock()

# Fonts
font_title = pygame.font.SysFont("Courier New", 46, bold=True)
font_med = pygame.font.SysFont("Courier New", 29, bold=True)
font_small = pygame.font.SysFont("Courier New", 21, bold=True)

# Colors
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
RED = (255, 60, 60)
YELLOW = (255, 230, 70)
ORANGE = (255, 128, 32)
BLUE = (80, 190, 255)
PURPLE = (160, 90, 255)
GRAY = (75, 75, 75)

# Main menu
MAIN_MENU_OPTIONS = ["START", "QUIT"]
main_menu_selected = 0
MAIN_MENU_BW, MAIN_MENU_BH = 320, 44
MAIN_MENU_Y_START, MAIN_MENU_GAP = 310, 14
MAIN_MENU_PULSE_MS = 900
MAIN_MENU_SOUL_BOB_PX = 3

# States
STATE_INTRO = 0
STATE_DIALOGUE = 1
STATE_FIGHT = 2
STATE_GAME_OVER = 3

game_state = STATE_INTRO
dialogue_lines = [
    "heya.",
    "you've been busy, huh?",
    "our reports showed a massive anomaly in the timespace continuum.",
    "it looks like this is where i stop you."
]
dialogue_index = 0

# Undertale-like player stats
player_name = "CHARA"
player_lv = 19
player_max_hp = 92
player_hp = float(player_max_hp)
karma = 0.0
invuln_frames = 0

# Soul + battle box (~2 px/frame red soul @ Undertale's 30 Hz → scaled for 60 FPS)
soul_size = 12
soul_speed = 2.0 * UT_SPEED
box_x, box_y = 250, 175
box_w, box_h = 300, 225
soul_x = box_x + box_w // 2 - soul_size // 2
soul_y = box_y + box_h // 2 - soul_size // 2
soul_rect = pygame.Rect(soul_x, soul_y, soul_size, soul_size)

# Attack timing
bullets = []
attack_order = ["bone_wall", "blue_orange_stream", "bone_cross", "blaster_volley"]
attack_index = 0
ATTACK_COOLDOWN = 2.0
last_attack_time = 0.0
fight_text = "* Sans is finally giving it his all."

# Turn system (OG-style command turn -> enemy turn)
ACTION_LABELS = ["FIGHT", "ACT", "ITEM", "MERCY"]
PHASE_PLAYER = "player"
PHASE_WAIT = "sans_wait"
PHASE_ATTACK = "sans_attack"
fight_phase = PHASE_PLAYER
selected_action = 0
phase_started_at = 0.0
sans_wait_duration = 0.0
SANS_ATTACK_DURATION = 6.0
BLASTER_WARMUP = 0.65
BLASTER_BEAM_TIME = 0.40
BLASTER_DAMAGE = 2.0
BLASTER_CHARGE_FLASH = 0.12
BEAM_SCREEN_FLASH = 0.09

beam_flash_until = 0.0

# Pre-rendered HUD/menu assets (generated once, reused every frame).
MENU_BX, MENU_BY = 10, 562
MENU_BW, MENU_BH, MENU_GAP = 185, 28, 10
MENU_BUTTONS = [("FIGHT", YELLOW), ("ACT", ORANGE), ("ITEM", ORANGE), ("MERCY", ORANGE)]

EMBEDDED_BLASTER_FACES_B64 = [
    "iVBORw0KGgoAAAANSUhEUgAAAEgAAABMCAYAAADOfPFRAAADWklEQVR4nO2cS47bMBBErSA3Sbb2QndJtuLRpK1zFy/k7eQsDgZwIU7BNd38aWSkayOMJZGy+FxsNskZbrfb7RCS+qJPheIFORQEGfp62ImWZfn1+Pc0TT8OO1AQ9CoEQSmln+/HaZp20bsGQb0Jul6vv9+Px+PxW433gBz+vNSLap8LCoJ6EbRQr5PbUooc6OHzcwlJl8vl8ngsJTEIak3QQi0/z/PZcz1a0CLHSxLKGcdx/IjgWhKDIEND7mh+IQLU/cMwDM8I85KjpMpTz+F9XqUgqJUHLU7vQPzRS8r7vHFTbnwVBNUSdHUSgetOp9P3Es/J9So+7+2tcN04jm+e+C0IauVBSbSoIidXHM+klIrKYUKUEGEHQb3joOEez7BXoMVryYHWdf3HE7jeUlnexvWywoNKPYhH63MncnqL4yYc8bnlRUFQqQe18oDP9iCv1HsIgnI9iL3nf5EaowVBrzYvtrf5uCCoF0EzxRN7lfc5VW49CGpN0GzMYrwqSeFBW0XS6z3ibT0W6x1J43uqciOSbu1Bub3UKvIquTOpXnF2gev1Emh5avRipQRhTJJEbpjfvCIHLdzKu5hU1MP1e3tbPJ9SEFQbB83Ci3iVheU5aPlafdDLPZ0PU4Tge8WsRm+CRuM3yuJVFCAKuV8rHlECgZiHAwEgBuW1Xh0bHtQ7H5REHqX3Ko+t6gmCagk63nsN/ObVPBK8RsU7rbMA3EuifBCF83gePB9H4JaCoNYelMhzOE5CL9VrJyPI9a6NxPUg2hv/QEFQ715s+hu5np/FNxxBK2/iFmUvw5HLgyfyHHyr/WZBUO3qjuneEkyKV6Wjd5DRqjyIybJWvQZBpQRZq0YX8eZz56FUyzGxpfNaaq0BZx3UGC4IapiTPj+eV2/eykT2kspPsTjSthQE9cpJt/Ki0lG58hxrXxr3jlamMwjqlZO2dhljtKzWKbO3qfL5/tqsAEfckZPeS076WLg/vXRXz1arTMKDWu1ZXYw5du8oGqN9Hq2r1R1MindHYe1zQkFQ713PLGv3DBOk/jOCioi9hLJK80RBUOuM4mSMsr07+azz3HvCq9SoWxFXm2EMglp7kNeTVMvBI3LrVffl1p+rIGjrWY1kRMalxHrvi1mNw7b6AyxqvxOpIcnnAAAAAElFTkSuQmCC",
    "iVBORw0KGgoAAAANSUhEUgAAAEgAAABMCAYAAADOfPFRAAADWUlEQVR4nO2cTW7bMBCFraI3abf2Qndpt+TRpG16Fy+sbXsWFQH80OBV4+GvpADvbYxEMCWbX94Mh8MM67quF8nUF/uSpC8oQSLI0dfLSTTP86+PP4cQflxOIBH0WQiCYow/319DCKeIriLI0dAqD1qW5c/76/V6/Vbyvtvt9n3reunzlT4PSwT19qCZok/ujN3v93sPEkDk4/H4XfJ+SAT1Imh+koOoM03T2ysCQAryG35/Lgl4v5cv1ZIkgnpFsZkIsMYZhmHYIswjxxLuw+MySRwdRdBZPGjO9J7W4qiZKpCU+xcjD2pF0JJIhJUZe56T6lH8+w8/b3oRKzX6QSKoVRRbnDUTooR13RNHI0Sp0nHGcRxfPU/q5xZBrQgaaEZTZ2pvgng8Fkdfz4tEUG0UmynvaE1OLzEpeN7caoEIqvWgodILjvKg0vuyRFCpB5WueT6b4FXjOG7Wi0SQI31BjvQF9d7VmJ5RoLRC2EutKpgiqBdBk7HWOWsmXUq6CColCJlljPHl9b0y3l4CWVqL9fKgyfjbtWrU1v5T6k5q6vNAvIbKvY+1yofkQb0qio8nKdydYc0ozxTXkbzVPF/ncZlYvB+fz9rPU0VxrzxoMrwIM8gkWV4A8nKF+3jjgiQvT9O+2N4EjY7bs7jrw6pt50Y1a1wQXNuTyFIUO7pPejHyJS9TT810LY9qJRHUiqArRQfuOUReg9qutVdfGsVSu2txPzwnCIZ35d5fBPXyoEhnKjBj3MnV+kQjxuMdUeu0UG0ftwjaK4qFf2uwt1drN4i9gjNb7mbFuJy5s8e1JlYEteruCM8ZZlJSldsFwvlTbR2JCebxVVHsRVB0ukitrtHa/TLOu6xxvD5tK/9hDxRBvaNYJJK8M6apa61ess6h5e7CKIrVErT+n49syvMiyPKS1E5+y5O8c2hMlGrSZ6lJs3iNxJkvj5N7hoPzsNTaslVL9yQP2uusxuSc/GMPKM2PuM7knXS0pLMaR51ZnZ2979TogBnmHVreWfX24q1xLenE4dH1oEBRxDoBmPvfWziq5HawWbsZqURbUhTr/d9fZsOTvJnj7gtvfMg7H8+q/XwiqHdNOhielHsaOVe9yYFE0FG7GtHJlFNn2PKc2nFTJYIur/UXhjXTg88EpBUAAAAASUVORK5CYII=",
    "iVBORw0KGgoAAAANSUhEUgAAAEgAAABMCAYAAADOfPFRAAADaklEQVR4nO2cTW6jQBCFzWhuMrO1F9wls+0+Gmydu7Aw28lZGFniaZwnKlUN1UCkehsUE35Ef65/3EzTNF1Con7Iu0LxgAwKghT9vJxE4zh+PLfDMAzPbUrp7XICBUHfhaBhJifn/Oe5bdv273N7vV5/HXlfQZCixjsOGmdbUrryTdM0S5+X3t/a60sKgvayQX3fv7/+bV1BPk7ab/VqsGVe3jAIqk1QP68wvE/XdXdLnAPhOEkv+z+dVyODj1tLUhBUm6BM5Egrdbvdfr/+31bB67GXw/Vzzh6XCYKqEdQr3odtTy1pcc9WWxQ2yJug0UgEezfNa7Ftsh4H2/Z4PKrkbkFQLRuUhRUFYVp8I+nFRtxLzgOSpNwN50kpFeV2QZA3Qbd5pdh2tG3bLu3fW4iPYJO4ziTFT5KCIC+Ceop7zkaO5t1wvyDJWjcKgrwIysa45GySyIZtCoJqE9Qbc67vJmuOFjZIUTwgRfGA9npAXdfdvaqFZ7qfIKh2Tbo7ETVL4gi6VEHQVoKS0iXAfqm3fpRADHIxltaFgYIgLxvUFX6XpRrxVtKklUd27l1VCIK8CEqKLWJvxuQgp0Mlr5QkJoenPnA9q1e19seCIO84qBMqc6gs8vQG98cwe7g2Plnoty3aJCaN79+qIOjoKdc8rzRsD1YUxGmSVpzPZ5X1ulAQVJug6+w9tJ6915QHCJDI4Q5qKTGsIMiboES9c7YpkrfiCbPSKQz2SpxrSUTBq669bhC014ziNHsVJgafl05VSFOzIAnn42kSac5obd0qCNo7Dkpko5Bzab18joQXcrYvj9fqO2u9WRDkPd2R/tuAonnkrb38tcdL3sv6DkgQVGG647705KUV0bJ2qWZsPV7yTlJcxHGU5l2DIK83DhuqAPIMICRV/Na+UajVmvk++HpaXBQ2aC8bNFFcwtOjL1pcGc2WlGb77J2wtda6oyZ91FvPvfAOBsQRM9eLmLxSL8W5X2lfzGp7oPBiR9WkrxS5srezdjWYNCnu4b6YdN6oSZ+topjl+elP33Up8ubuBMcxUpyz1jZGRfEsNigZSSqtJELWCqD2flqp12KFF6vtxZJCkrXuIvXWtQibvaMXOVAQtFcclASSvH5Dw+q1vMiBgqC9f4FK+1UYr5XlrN37/FAQdPla/wBQbq7akqSbnAAAAABJRU5ErkJggg==",
    "iVBORw0KGgoAAAANSUhEUgAAAEgAAABMCAYAAADOfPFRAAADOklEQVR4nO2cSW7jMBBFpUZukt7aC90l2YpHE7fJXbSQt8lZ3BCQAtwfKRWLg80g/wOG4UEyJT3XSGq8Xq/XgVL1R/+I4glKEAn6KScoxvi+P7TXw28/Qb1q7MWLjeM47s8yHqFnmqZpfz6dTs+PGBcJMvQ0dELOsixv331+Pp//7s/btn2UkHS5XD5ztidBrQiK4GHmeX4p2d5SLklCjmzvtbkkqDZB8evKhxBej2yH5oXE5uRKI0l+zyIZvaUlElSboADk4BWT/7x8T650KTkotCnye8Mw/DcuIUzGK99L9WokqBZBYyIB67quR69rKzdfS/VqJKiUoMvXf9Xr3UT4urYOfu9bG4myvB8JKiVoNWyIRs6jhSTligTlEpQaMYfOyEHh+PE4LJtFglpl86FzciySJEe0RIJya9K1cydLmNs9yjtilYAEeW3QvcnpTZijkSBDPEGGeIJaxUELVOh610EEfSgSVPsEbdv2IbHCT9JOTA7tJMhrg4QOiQdQEmFqn/cuycE0G4r/DhLkJUjrI2my+mNSkWzl7dA74ThKczoSlBsHWfWSRakwIok3ncuqcZNGrmVzNBuKn4tIUC5BXltkSa50CGGoodSKYCmJJKi3OYqbEWdZ0mxFK5Gg3me5tlbp7BISVErQBN4C5+OId5vnuYsZ+1Y/DMdveUMSVErQSYmHbvppbzmzR1tLm8eN73OO4r1W+0TIinE77KdpPXAt/vF2eHH/WtUA9+tdIUAblEuQNndvVGxNaUe21RwBjSCtfiVib77W7I4NZjvg+i65Evh+avZvZdO4Wid1f2grrVU/2vHSBpXGQefEGenemVsi6/u5WTtWPLWczLJxJCiXIKzbRCUHw9mh6A1SbRKuvkldjYP7x/VpWlcDj4c16VY2aHF6JczdLBuDEbDYOnnfqufceD9XpRGPRxsnbVBpV2M1rmBpd8EiM9V25XZTrBo3CWqVzXs7nCLNG1o5ISr1nh5WJM4Vh/e++0tUSPKS6CUhdzutTpVKPG1Q7b7YDHGHkJR65wOR975AWDm0pEXK3nuMkKB7dVaDsz/mzdJT47LaIkGt72EWjW7Ho6RVPr0iQcOx/gFWFXzeVUla6QAAAABJRU5ErkJggg==",
    "iVBORw0KGgoAAAANSUhEUgAAAEgAAABMCAYAAADOfPFRAAADRElEQVR4nO2cTXKjMBCFTWpuMtnihe4y2aKjwda5CwuzTc7iKVfRFeeV2936ActV722IbcAgf7xuSa10l8vlcqBUvekfUWwgh0iQITaQITaQoT+HRjRN0+d1OwzDv9vXIYRw3fZ9//cZ10WCDHWt5EFd13XXrVyPECQSsvYWCdrag5Zl+c7xCDnueDy+P9ovxvix/nkqIQk9zisStBVB3eoZ4ziecgiyyKlNUu7xJKg2QRNEF+9+8osJebnSSMAoaB0fQvjykE+CahG0rFFHfgHxHu1Zxv285HmFJFjR6nw+f9163zzP83VLgvYiaF5b3JJGyo13VBVel9djZL9hGB56Fj2olKAFvMciB/fbihzr/OI1VlSzMmwSVErQbHiPRk4rkvxIoliqF5GgUoIi5DPa561LPAnvQ65f8yISlEuQlfnGFyHHKy1/IkG5BO2dz+wl6z6wj0aCUgmq3et+dS8iQYbYQIbYQFvNaoxrRvoq0U3LoC2RoNoEnWFs91WEfUrvE0CCUgmS3myM8e4B2hhvK739XK/B45lJl3qQ9xkdjfkxmQHdiiQk5s51JN2HVLSJ6EG5BGFLej1HGwuW2YXSuXn8fqtKAz0VayAtjyVBuQRJS46KFwlhOOuBhEi+pM0qtCLOi7VeJz2vpJV6kdd7aoketDVB0Vkl4d2vtiRaWVFXEwkqJWj4edZPj+a6pQqktd6+Vukm71vRlQRt5UH9michMfJa6yMJaahcj0DJ+TE/0zJo1ijutdpngbUVeBw+26njQ9p1aPVH3vNr1ymy8il6UC0P6hPXYqSO/6SuGvKeXzuvNVohIkG5HoTRYIA1EdgnwjWm3jzI27fy9t3Qm5AUjLZCFivMtq5RDGu1A44PYd/qWauTNSEhKHwiUPSg2ms1IkQPbZ2Wd35KPAI9wBvVkGhcZ6/lUd61JySoNJOejEp6LQppfSItI5b3cd28le9gXxDvx7u6WmsHElTqQcGZceaq1oyrFoW8HqaJBJUS1BvzY9Zxd37BX3PgmKlrI5k4Aoj1zLn5F3vze+VBoZIXWeNFqfVKufJ+Pz3oWeNBllJnRrX/K5Qrjge1Uic9JJJQOnuhVZVYyp2vowcdHus/ygxeRDfbYTkAAAAASUVORK5CYII=",
    "iVBORw0KGgoAAAANSUhEUgAAAEoAAABMCAYAAADKiSFsAAADMklEQVR4nO2cTW6DMBCFQ9WbtNuw4C7tFh8Ntu1dWJBte5ZUSBkpfe0w4z9Covc2SBEEx3yZeR7bNOfz+XygTD3Zp1DsqAiRKKfYUU6xo5x6PuxE4zh+Lse+79+W4+l0+l6O0zRN15/fSiTKKXaUU+wop5pcZz5CbEm9PoTwvhylPRKj2rZ9XY7DMHyUuE/q9SSqdtYbL08o93ohydLVeUlk5V5PomoRNQIJEjtQmg+KJclLRtM0zXLUYq60M5UsErWVM++VJ4LZKpckFJIh99HIknaGEJLuR6JKEzU6icjNhqnCdkmMPB6PL2vnd133tXaeiESVcubokFFyfakYpDnzVM3z/IsYiWHafTWRqFIxSnwQqlY2Ky0hUsjSZMU0ElUqRsl/elAceGmSSscoFP4ObL/WHyQqN0ZZfijsNCZZssaoWt2KROXGKM1v1FbtGGVJq6SSqNQYdaux2l6k1atIlFPsKKfYUbU7ap7nL2v8tEctWU3zUGsiUbVq5vOFIq2qcC/6Z1ZmVSQqlSjvbEWAJ7FVdSG3OuC9ns68dIyK/Q93XdcpFcKsJxxLEJIgsyzeMaP8DhRjVOkKpwi9U+waS6sq4a0eYCzBMSq2B2eQtVo/K5y1fZQQ1MKTlVgU66diY5+llVmgqNUqnNe713XmfeaqEvyerepnzHpbERUiV4WUkmTFrVbXkKhSRAkhwyVbSfbDLCHZbyuiNFn+Ckn01qZI1FYxav7rsz7Wxn7yRHOFpIu01cfo+K2xHYpElSaqU3oen6xVp9KyFI4hre/Vspk1NsV2eWMqiSpN1FGJCZa8Y7rYrFnrezWRqNpZr1F2CGjVBk3WPryrz11VB4t43FHhFYkqRRTukkKhL7m1M9eytObfvDtDSdRWzrxV1nHHzvNp7z2wpPksIdtaBy+f933PnQu72AszGFkLHbSVtWLXcCJRqWtSWTN/tHez5Ga3lDVPMWLWq1XhDJHzcRi7ZPZFYoLEDq16gE4fZ3rlvFT/5l01SKJq1aMGIMtbIURJVrPqQkh0aoUU28161F7qUROM+VJjQ2xsiXXs2vV878Gj+agh0++krqLJFbPewacfHK+BbndleuUAAAAASUVORK5CYII=",
    "iVBORw0KGgoAAAANSUhEUgAAAEgAAABMCAYAAADOfPFRAAAC/0lEQVR4nO2cQc6bMBCFQ9WbtFuy4C7tFo4G2/x3YRG27VmokHgqGvVlbGMwf/reBgUFJzFfnseewdU8z/Mto4Zh+FiOXdf9XI593z/+9b62bX8sx2mafm/P13X9bdsO3ofXTdM0y3Ecx/FVu7n0JWdj76ivuRts/97Bx5ak5/P5azne7/fv6/vmLQkggwntgHi0A0JzkwOJoLMJYiThjkPwHksYhPO4HqRUVVWdQQ4kgkoRBDFvsUQxbUgqIhFUmqB6jWvsKJaqs7wHEkGlCcpF0tnkQCLIUZV7LvZuEkGO1EGO1EGO1EGO1EGO1EGO1EGO1EGO1EFXmYsxhWY1SkkEXb2DxlW3i6p4B11dxWbz0+o9WBfCOhE86OzsBZMIyj2KTebOxxJor/dk82OxJNmcPggNlQjKRdAUeedtHBN7fShJofFSai5fBOUiaDSxis2ls/qgpmmy5MMYSfZzLRl43XVd0ueJoL1x0ES8g11n45fQHDuLg5hY+973std7XiSC9nrQGDhPggecVZXB2gcplshUiaC9HlQRL8B1dtRKVawHhQrfk7XnkSaCUj3Ieort8VzkHC3rSXY09uaUIijVg9h6zHAQOUd5UKh3Mi8SQbEElfKW50kEebL9IYJCRzFb+f6/ajCrAiIolKAr56ZKSgTl7qC+7x/sKcIrK/V7i6Bca9L9J6Tm1e8IHa1FUChB7FnTdxF7stHKrlGLoKMrzHqSHTh7LrV3Tsk8VgTtXQ+KzUPZmkPIy6ym5sW8vJZdGUWVR2ieTwSlehCLF1qS62YZWJARG394iq0TYnuFePGdCEolKLYqYiSrATi/t8oCyl1T6e0ZIoJKV9p3pk7os0kE7SWod1zeVpFeRTaStvsV4Xd51R8iaC9BjYk84SU2rkG8Y3PgoXcqt9geat7ealYi6KhRrHV2mGKzaytGGIu8WTUr231v7zMeImgvQfV6Z9l/lo1eR60HgZDUiFyV9qU9aFzjCJBl44rY2TojEOdj22WkMw/0JA+6vdYfTWQu73iU7MQAAAAASUVORK5CYII=",
    "iVBORw0KGgoAAAANSUhEUgAAAEoAAABMCAYAAADKiSFsAAAC70lEQVR4nO2cQXKDMAxFodObtNuw4C7tFh8Ntu1dWIRtexY6mUEzVBNFwpZxSP7f0EmN7cLrl3As6krR+Xz+uRzHcRzXn4cQPte/P51Ob5VBwzB8r8/v+/7rcmzbtr0cm6Z5v/Y5jR877jRNv9f6J/HxuV4sg0BV9apdBOkOxKrruo/lx6j+aB5WkqySSCKBKC+iOElh8YhHEXmTJhDlRRS/8v1CGJHFo6G3d/D+t4qibKpAlBdRPN/h4nlOLFlSe4qSW8mgvEnzIC3akUCUt0dJXsXzLCKLjqu8ydUzqB9r/9KTAPdcSSAqlSh+pYNwRzRpBFn7kbxwK6Hc86x5IYjyzsyDcOX57/lqAz+PR09rdKR2Ur+8f74aQPOSCNT+ThCVShT3pF7Jo6QoqPWbS97zAFG58igSeYUWtXKvPsSSuXVeIMqo2uvOBSUKSSIiKarVdV2vz6O8h57dtNWE2HmAqFIeFTZGC629RkgqSVo7RL178ajASLHeUd7een7sedb+NCHqeXtUiPzf3tpvajsuLTO3CkR5e9TRvvfz9jQQlftZ797lvUoBop6dKK5U7wRRRuFCGYULtVceda/5lPd8QJRRDx/1ghPZIKq0R5XyqlzzAFF7E1WarNzjgqjSUa8V9jN5S6pp8R4XRJXyqFKZeu7xQBQEFVFNexuh24JHGVXP8zxbGz+zQNRR16OmZT9Urvq/WIGooxI1Zq4ojRWIOlrUG5QqKV6Xt7dAVCmPGoTKTGuU89rZt3UemkDUXkRNxn3g0p3W6u9Wn/+rZLAS40UWiNrbowKrAOXiNbxt20atWkj9SPkWteu6Lim6g6i9iGpYpaU1k9a8ybonk/rh4/L3VFHVVmzeCKJyEzUY3zcgvdMuVVf2jf+LilqU3voMCaJyExUUQrQ3VVgrNSNqZW6SJXmaJhCVi6hB8Cb6zl8iyepN2t4BjWSeX914q4/J00ggKrdH9UIVuUaS154ArWqKv5ch9f2fIKqy6Q/rGDi4ZKSkWwAAAABJRU5ErkJggg==",
    "iVBORw0KGgoAAAANSUhEUgAAAEgAAABMCAYAAADOfPFRAAADRUlEQVR4nO2bTZKbMBSEh1RukmzxgrskW/lo9nZyFxZmm5zFKafcVVRXHi2EZMike0PZMEKj9/n9Ibr7/X5/W9D1ev3xOJ7P5++P4+VyeZ+fx/csXBedj64fhmF4HMdxHEv+PpoXn+fronX4lHPz/1mf1/7BOdOiudfVkrqfIj2SCapNUGv1ff9l7oNaa0bWH5JSSt/m501Qa4IuIjqUCtGsVLnRVskEtSLosjFvUarlgzC/KC/j/4NlgrYSNAgLsKXXZtC1xb4H81M+DdGTZYK2EtSLvAR5A2o2WIprG5yHthIGUjhvie7HhCjfA5mgWlFsIF8UrTxbapqmX/PPM4sX+arb7fZzfh+QEpHE82QfFfkeyATVIqgXvogtBXJOp9NXujTrt8+C5TGPruu6v40LkjC+IkTJBO1VzY9P0jjawPKIcqofwz4PZEbjppQWO6RQLsEmqDZBw8Yqu1QctWqNp2SCWvmg8elj2BKcl8yizaKvyRV3DzA+fBJ8FM+P87FcmaDaBPWUD8EyUZ6EzBff4/NaUqL7czTDfNhXlvaXTNCr86DhaTmu7qNaCeLzilS+nqNbbm2mZIJaETSIah6W52OpcsdZ2zlkMlkmaCtBV/HbjvIhVu5uC9WxXDuOyn/U/E1QbR80BRaJfsuRTwAJuXnRWtIU0Uxk1AUwQVsJSmSZ3OdMnNnmPitXUUX5Hr6vinpqh50Jal3NQ1HNxHkRP9WILByRxOSszYzX9pNMUC2CUmY+UvoUISKJv4+qfCXepeue9F4+KIkno7n5UERC9KyfM15FKu9XYnLck947iqWAJFiKo1ZksVKfUvpmwFof6SjWuqOYBEmRIt8TfVaEwfdt9TksE/SqnvQQ72Vc3AmWq6jqjvIy7+54kTpVzZaKLcs7w2qJa6ta5ED2QXvtD0oU3SDeH1TayYxqtNqEmqC9fFBpH4Y7grwviDPvVuRAJugoBKmog92wmI8iBmpFDmSCjkbQJJ42cD8o0tbMPFcm6GhvPffkM1SVXtpLriUTdNT35vtMktR7Ya1lgo4Wxf41mSAhL5CQFyg3itV6i+ajyQQpPXrFtfYJfkSZICEvkJAXSMgLJOQFEvICCXmB3pb1G39ljrMLAp2RAAAAAElFTkSuQmCC",
    "iVBORw0KGgoAAAANSUhEUgAAAEgAAABUCAYAAAAh+XGnAAADs0lEQVR4nO2cQY6jQAxFYTQ3mdmSBXeZ2cLRyLb7LizCtvssjJBiqfU1jl0uE+ju/zdISUFK1MN22Q7tuq5rE9D1en3djsMw/Kk5X4TXWZblfTvO8zxvx77v++3Ydd2vkt+R65SeJ/oROek76WftypdKVtSSkDOO49/tOE3TSw0JUeJJUBZBy33lcUW1cZfL5fd2FBuH5FnXQcn4pmlePpJg2TIhTohs27b9OC9LJCiLoPm+ArLi2rMs4xwkhIQk4efDMKyZ3o0EZRE0Om0PjsPP95bmrSSOknkJ6SRob4Lau9XXhF6r1CZFhaTKUfN22vnWONqgKEEY8U5gezRycFzU9ojNiAoJiV6PBEUJQtvRwwrg91nkZNsi/B69mRU/kaBSgiSO0OKeGXbZZ1EtSdoejQRlRdIXJc75T/xxqKyIH+dpZRNIUC1Bo0HGWciJzgvH4V6OBHkJ8uaKnx331Nq42nmSIC9BmLvVNB0UMUcl87vdbm8eInHHQIKy4qAJIlDMUZ+VJMwgart6LR4iQaUEabvdKGHPIstbX7Ny0Pg9CSolCO/gBGSgt9NyuTKu7/u3R3u5qLR5eXsJkDjNNpGg7O4O645rtfIsb2dVdlHeXLRGIAmKEuSNrEUPKqi44i5vky2NEIswErSXDSpVabag1vZkiQRl9wd18CxbZJR2kj1b7O7Ym6ABegGRGIyoJe+CkTPu0fYW9lkLKaVdurRBe3mxDmwRVgOsPZzI2svheKu3EMmp9XokKIugXok4caWFJCQn2qGPtkuzYVY3Cn7u7dgnQdHuDu1Oz87uUGvFvdJsUfS62vy17lgSVNth1hneAr8X8qxukFrvonVpYNwm89MifsxCYKcZCYpWNYSgxbkLR6+xV73M29/jzSRifQ9FgqJVDfRCvdHlqnk73Jvhs67ZMititqoSaHu0iBxr9ygSFPVi4g3ae/en9ox6K5V4PsZbpR3/0eyA1g3LqsZee7Gbkt/JyhBa8ZZGiHcvZRFmxWO0QYZa779/F/AG8iyXni/yvlEBbVVpnkf754D3fBKUlQ/qCiutKCSmlMDarAB6P69I0F456SnoxYQELzloKyQu8/4/vlYkKPvdHaLSZ7n2P6hRcjE/5M2IikjQWbo7uuB7f1Ds7vjs3R2jkT/5LOLbX46yQVPh21OOlpZT59tfjvZiY+Ebn46StofzxmWMg7K7O2ajjvTVRILOEkmfRewPOjqjKHpWt2q2SuM22qCsqsZ3FQkyxBtkiDeoeax/4DUX+z75ca8AAAAASUVORK5CYII=",
]

EMBEDDED_SANS_PNG_B64 = (
    "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"
)


def make_embedded_sans_sprite():
    png_data = base64.b64decode(EMBEDDED_SANS_PNG_B64)
    return pygame.image.load(io.BytesIO(png_data)).convert_alpha()


sans_sprite = make_embedded_sans_sprite()
sans_sprite_scaled = pygame.transform.scale(
    sans_sprite, (sans_sprite.get_width() * 2, sans_sprite.get_height() * 2)
)


def make_menu_button_surface(label, color):
    surf = pygame.Surface((MENU_BW, MENU_BH), pygame.SRCALPHA)
    pygame.draw.rect(surf, color, (0, 0, MENU_BW, MENU_BH), 3)
    txt = font_small.render(label, True, color)
    surf.blit(txt, ((MENU_BW - txt.get_width()) // 2, 3))
    return surf


menu_button_surfaces = [make_menu_button_surface(label, color) for label, color in MENU_BUTTONS]
menu_cursor_surface = pygame.Surface((10, 10), pygame.SRCALPHA)
pygame.draw.rect(menu_cursor_surface, RED, (0, 0, 10, 10))


def make_main_menu_button_surface(label, edge, inner):
    surf = pygame.Surface((MAIN_MENU_BW, MAIN_MENU_BH), pygame.SRCALPHA)
    pygame.draw.rect(surf, edge, (0, 0, MAIN_MENU_BW, MAIN_MENU_BH), 4)
    pygame.draw.rect(surf, inner, (4, 4, MAIN_MENU_BW - 8, MAIN_MENU_BH - 8), 2)
    txt = font_med.render(label, True, edge)
    surf.blit(txt, ((MAIN_MENU_BW - txt.get_width()) // 2, (MAIN_MENU_BH - txt.get_height()) // 2))
    return surf


def make_main_menu_glow_surface():
    surf = pygame.Surface((MAIN_MENU_BW + 20, MAIN_MENU_BH + 20), pygame.SRCALPHA)
    pygame.draw.rect(surf, YELLOW, (4, 4, MAIN_MENU_BW + 12, MAIN_MENU_BH + 12), 2, border_radius=4)
    pygame.draw.rect(surf, ORANGE, (0, 0, MAIN_MENU_BW + 20, MAIN_MENU_BH + 20), 1, border_radius=6)
    return surf


main_menu_button_idle = [
    make_main_menu_button_surface(label, ORANGE, GRAY) for label in MAIN_MENU_OPTIONS
]
main_menu_button_selected = [
    make_main_menu_button_surface(label, YELLOW, ORANGE) for label in MAIN_MENU_OPTIONS
]
_main_glow_base = make_main_menu_glow_surface()
main_menu_glow_frames = []
for i in range(12):
    phase = (2 * math.pi * i) / 12
    alpha = 60 + int(110 * ((math.sin(phase) + 1) * 0.5))
    frame = _main_glow_base.copy()
    frame.set_alpha(alpha)
    main_menu_glow_frames.append(frame)

# Gaster blaster data/cache.
gaster_blasters = []
blaster_rotation_cache = {}


def make_blaster_fallback_surface():
    # OG-inspired blaster skull (transparent background).
    surf = pygame.Surface((118, 74), pygame.SRCALPHA)

    # Skull + snout
    pygame.draw.ellipse(surf, WHITE, (8, 10, 80, 50))
    pygame.draw.rect(surf, WHITE, (66, 25, 40, 18), border_radius=7)
    pygame.draw.ellipse(surf, BLACK, (8, 10, 80, 50), 2)
    pygame.draw.rect(surf, BLACK, (66, 25, 40, 18), 2, border_radius=7)

    # Horns / top spikes
    pygame.draw.polygon(surf, WHITE, [(20, 12), (13, 1), (28, 9)])
    pygame.draw.polygon(surf, WHITE, [(48, 10), (53, 0), (57, 12)])
    pygame.draw.polygon(surf, WHITE, [(74, 12), (84, 2), (78, 15)])
    pygame.draw.polygon(surf, BLACK, [(20, 12), (13, 1), (28, 9)], 1)
    pygame.draw.polygon(surf, BLACK, [(48, 10), (53, 0), (57, 12)], 1)
    pygame.draw.polygon(surf, BLACK, [(74, 12), (84, 2), (78, 15)], 1)

    # Eyes (hollow sockets)
    pygame.draw.ellipse(surf, BLACK, (21, 25, 16, 12))
    pygame.draw.ellipse(surf, BLACK, (52, 24, 16, 13))

    # Mouth slit
    pygame.draw.line(surf, BLACK, (69, 34), (102, 34), 2)

    # Lower jaw fangs
    pygame.draw.polygon(surf, WHITE, [(72, 43), (76, 53), (80, 43)])
    pygame.draw.polygon(surf, WHITE, [(86, 43), (90, 53), (94, 43)])
    pygame.draw.polygon(surf, BLACK, [(72, 43), (76, 53), (80, 43)], 1)
    pygame.draw.polygon(surf, BLACK, [(86, 43), (90, 53), (94, 43)], 1)
    return surf


def make_og_blaster_variants():
    # Build multiple pre-baked OG-like variants with different eye expressions.
    variants = []
    for eye_offset, right_eye_tall in [(-2, 0), (0, 2), (2, -1), (1, 1), (-1, 3), (3, 0)]:
        surf = make_blaster_fallback_surface().copy()
        pygame.draw.ellipse(surf, BLACK, (21 + eye_offset, 25, 16, 12))
        pygame.draw.ellipse(surf, BLACK, (52, 24 + right_eye_tall, 16, 13))

        # White highlights for the OG flash feel.
        pygame.draw.ellipse(surf, (215, 245, 255, 230), (25 + eye_offset, 28, 4, 3))
        pygame.draw.ellipse(surf, (215, 245, 255, 230), (56, 27 + right_eye_tall, 4, 3))
        variants.append(surf)
    return variants


BLASTER_FACE_SURFACES = make_og_blaster_variants()

# Pre-baked bullet sprites with transparent backgrounds.
bullet_surface_cache = {}


def get_bullet_surface(width, height, color, kind):
    key = (int(width), int(height), tuple(color), kind)
    cached = bullet_surface_cache.get(key)
    if cached is not None:
        return cached

    surf = pygame.Surface((max(2, int(width)), max(2, int(height))), pygame.SRCALPHA)
    w, h = surf.get_width(), surf.get_height()

    if kind == "bone":
        # Pre-baked styled bone sprite: colored base + white bone detailing.
        horizontal = w >= h
        base = tuple(max(0, min(255, c)) for c in color)
        outline = tuple(max(0, min(255, int(c * 0.75))) for c in base)

        if horizontal:
            cap = max(4, h // 2)
            shaft_h = max(2, h - 6)
            shaft_y = (h - shaft_h) // 2
            pygame.draw.rect(
                surf, base,
                (cap - 1, shaft_y, max(2, w - 2 * cap + 2), shaft_h),
                border_radius=max(1, shaft_h // 2),
            )
            pygame.draw.circle(surf, base, (cap - 1, h // 2), cap - 1)
            pygame.draw.circle(surf, base, (w - cap, h // 2), cap - 1)

            # Dark colored outline for stronger edges.
            pygame.draw.rect(
                surf, outline,
                (cap - 1, shaft_y, max(2, w - 2 * cap + 2), shaft_h),
                1, border_radius=max(1, shaft_h // 2),
            )
            pygame.draw.circle(surf, outline, (cap - 1, h // 2), cap - 1, 1)
            pygame.draw.circle(surf, outline, (w - cap, h // 2), cap - 1, 1)

            # White "bone core" overlay so blue/orange still read as bones.
            core_h = max(1, shaft_h // 3)
            core_y = h // 2 - core_h // 2
            pygame.draw.rect(
                surf, WHITE,
                (cap, core_y, max(2, w - 2 * cap), core_h),
                border_radius=max(1, core_h // 2),
            )
            pygame.draw.circle(surf, WHITE, (cap - 1, h // 2), max(1, cap // 2))
            pygame.draw.circle(surf, WHITE, (w - cap, h // 2), max(1, cap // 2))
        else:
            cap = max(4, w // 2)
            shaft_w = max(2, w - 6)
            shaft_x = (w - shaft_w) // 2
            pygame.draw.rect(
                surf, base,
                (shaft_x, cap - 1, shaft_w, max(2, h - 2 * cap + 2)),
                border_radius=max(1, shaft_w // 2),
            )
            pygame.draw.circle(surf, base, (w // 2, cap - 1), cap - 1)
            pygame.draw.circle(surf, base, (w // 2, h - cap), cap - 1)

            pygame.draw.rect(
                surf, outline,
                (shaft_x, cap - 1, shaft_w, max(2, h - 2 * cap + 2)),
                1, border_radius=max(1, shaft_w // 2),
            )
            pygame.draw.circle(surf, outline, (w // 2, cap - 1), cap - 1, 1)
            pygame.draw.circle(surf, outline, (w // 2, h - cap), cap - 1, 1)

            core_w = max(1, shaft_w // 3)
            core_x = w // 2 - core_w // 2
            pygame.draw.rect(
                surf, WHITE,
                (core_x, cap, core_w, max(2, h - 2 * cap)),
                border_radius=max(1, core_w // 2),
            )
            pygame.draw.circle(surf, WHITE, (w // 2, cap - 1), max(1, cap // 2))
            pygame.draw.circle(surf, WHITE, (w // 2, h - cap), max(1, cap // 2))
    else:
        # Pellet rendered as circle on transparent background.
        radius = max(2, min(w, h) // 2)
        pygame.draw.circle(surf, color, (w // 2, h // 2), radius)

    bullet_surface_cache[key] = surf
    return surf
ost_buffer = None
ost_loaded = False


def init_baked_ost():
    global ost_buffer, ost_loaded
    try:
        if not pygame.mixer.get_init():
            pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=1024)
        if not ost_loaded:
            ost_buffer = io.BytesIO(base64.b64decode(OST_AUDIO_B64))
            pygame.mixer.music.load(ost_buffer, OST_FORMAT)
            pygame.mixer.music.set_volume(0.55)
            pygame.mixer.music.play(-1)
            ost_loaded = True
            print(f"[OST] Loaded embedded track: {OST_TITLE}")
    except Exception as err:
        print(f"[OST] Failed to load embedded track: {err}")


def reset_run_state():
    global game_state, dialogue_index, player_hp, karma
    global soul_x, soul_y, attack_index, last_attack_time, invuln_frames
    global fight_phase, selected_action, phase_started_at, sans_wait_duration, fight_text
    global beam_flash_until
    game_state = STATE_INTRO
    dialogue_index = 0
    player_hp = float(player_max_hp)
    karma = 0.0
    invuln_frames = 0
    soul_x = box_x + box_w // 2 - soul_size // 2
    soul_y = box_y + box_h // 2 - soul_size // 2
    soul_rect.topleft = (soul_x, soul_y)
    bullets.clear()
    attack_index = 0
    last_attack_time = time.time()
    fight_phase = PHASE_PLAYER
    selected_action = 0
    phase_started_at = time.time()
    sans_wait_duration = 0.0
    fight_text = "* Sans is finally giving it his all."
    gaster_blasters.clear()
    beam_flash_until = 0.0


def start_player_turn():
    global fight_phase, phase_started_at, fight_text
    global beam_flash_until
    fight_phase = PHASE_PLAYER
    phase_started_at = time.time()
    bullets.clear()
    gaster_blasters.clear()
    beam_flash_until = 0.0
    fight_text = "* What will you do?"


def start_sans_wait(msg):
    global fight_phase, phase_started_at, sans_wait_duration, fight_text
    global beam_flash_until
    fight_phase = PHASE_WAIT
    phase_started_at = time.time()
    sans_wait_duration = random.uniform(5.0, 10.0)
    fight_text = msg
    bullets.clear()
    gaster_blasters.clear()
    beam_flash_until = 0.0


def start_sans_attack():
    global fight_phase, phase_started_at, last_attack_time, fight_text
    global beam_flash_until
    fight_phase = PHASE_ATTACK
    phase_started_at = time.time()
    last_attack_time = 0.0
    fight_text = "* Sans attacks!"
    gaster_blasters.clear()
    beam_flash_until = 0.0


def spawn_bullet(x, y, vx, vy, w, h, color, kind):
    fx, fy = float(x), float(y)
    bullets.append({
        "rect": pygame.Rect(int(fx), int(fy), int(w), int(h)),
        "fx": fx,
        "fy": fy,
        "vx": float(vx),
        "vy": float(vy),
        "color": color,
        "kind": kind,
    })


def spawn_attack(name):
    sc = UT_SPEED
    if name == "bone_wall":
        safe_lane = random.randint(0, 5)
        phase = random.randint(0, 1)
        lane_h = box_h // 6
        for lane in range(6):
            if lane == safe_lane:
                continue
            y = box_y + lane * lane_h + 4
            color = BLUE if (lane + phase) % 2 == 0 else ORANGE
            spawn_bullet(box_x - 60, y, 5.4 * sc, 0, 52, lane_h - 8, color, "bone")

    elif name == "blue_orange_stream":
        for i in range(8):
            color = BLUE if i % 2 == 0 else ORANGE
            x = box_x + 18 + i * 34
            speed = random.uniform(3.0, 4.3) * sc
            spawn_bullet(x, box_y - 25, 0, speed, 16, 38, color, "bone")

    elif name == "bone_cross":
        center_x = box_x + box_w // 2
        center_y = box_y + box_h // 2
        phase = random.randint(0, 1)
        v = 3.0 * sc
        for i in range(-5, 6):
            vertical_color = BLUE if (i + phase) % 2 == 0 else ORANGE
            horizontal_color = ORANGE if (i + phase) % 2 == 0 else BLUE
            spawn_bullet(center_x + i * 10, box_y - 20, 0, v, 12, 28, vertical_color, "bone")
            spawn_bullet(box_x - 20, center_y + i * 9, v, 0, 28, 12, horizontal_color, "bone")

    elif name == "blaster_volley":
        spawn_gaster_blaster()
        if random.random() < 0.5:
            spawn_gaster_blaster()


def spawn_gaster_blaster():
    side = random.choice(["left", "right", "top"])
    target = pygame.Vector2(soul_rect.centerx, soul_rect.centery)
    if side == "left":
        origin = pygame.Vector2(box_x - 80, random.randint(box_y + 30, box_y + box_h - 30))
    elif side == "right":
        origin = pygame.Vector2(box_x + box_w + 80, random.randint(box_y + 30, box_y + box_h - 30))
    else:
        origin = pygame.Vector2(random.randint(box_x + 40, box_x + box_w - 40), box_y - 65)

    direction = target - origin
    if direction.length_squared() < 1:
        direction = pygame.Vector2(1, 0)
    direction = direction.normalize()
    angle = math.degrees(math.atan2(direction.y, direction.x))
    now = time.time()
    gaster_blasters.append({
        "origin": origin,
        "direction": direction,
        "angle": angle,
        "face_index": random.randrange(len(BLASTER_FACE_SURFACES)),
        "warmup_end": now + BLASTER_WARMUP,
        "beam_end": now + BLASTER_WARMUP + BLASTER_BEAM_TIME,
        "beam_started": False,
    })


def point_segment_distance(px, py, ax, ay, bx, by):
    abx = bx - ax
    aby = by - ay
    apx = px - ax
    apy = py - ay
    ab_len2 = abx * abx + aby * aby
    if ab_len2 <= 0.0001:
        return math.hypot(px - ax, py - ay)
    t = max(0.0, min(1.0, (apx * abx + apy * aby) / ab_len2))
    cx = ax + abx * t
    cy = ay + aby * t
    return math.hypot(px - cx, py - cy)


def update_gaster_blasters():
    global player_hp, karma, invuln_frames
    global beam_flash_until
    now = time.time()
    for blaster in gaster_blasters[:]:
        if now > blaster["beam_end"]:
            gaster_blasters.remove(blaster)
            continue

        if now >= blaster["warmup_end"]:
            if not blaster.get("beam_started"):
                blaster["beam_started"] = True
                beam_flash_until = max(beam_flash_until, now + BEAM_SCREEN_FLASH)
            start = blaster["origin"] + blaster["direction"] * 40
            end = start + blaster["direction"] * 1100
            cx, cy = soul_rect.center
            dist = point_segment_distance(cx, cy, start.x, start.y, end.x, end.y)
            if dist <= 13 and invuln_frames <= 0:
                player_hp -= BLASTER_DAMAGE
                karma = min(float(player_max_hp), karma + 12.0)
                invuln_frames = int(round(14 / UT_SPEED))


def draw_beam_flash_overlay():
    global beam_flash_until
    now = time.time()
    if now >= beam_flash_until:
        return

    t = max(0.0, min(1.0, (beam_flash_until - now) / BEAM_SCREEN_FLASH))
    alpha = int(110 * t)
    if alpha <= 0:
        return

    overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    overlay.fill((180, 240, 255, alpha))
    screen.blit(overlay, (0, 0))


def damage_from_bullet(bullet, moved_this_frame):
    if bullet["kind"] == "pellet":
        return 1.0
    if bullet["color"] == WHITE:
        return 1.0
    if bullet["color"] == BLUE:
        return 1.0 if moved_this_frame else 0.0
    if bullet["color"] == ORANGE:
        return 1.0 if not moved_this_frame else 0.0
    return 0.0


def update_attacks(moved_this_frame):
    global player_hp, karma, invuln_frames

    if invuln_frames > 0:
        invuln_frames -= 1

    for bullet in bullets[:]:
        bullet["fx"] += bullet["vx"]
        bullet["fy"] += bullet["vy"]
        bullet["rect"].x = int(bullet["fx"])
        bullet["rect"].y = int(bullet["fy"])

        if bullet["rect"].colliderect(soul_rect):
            dmg = damage_from_bullet(bullet, moved_this_frame)
            if dmg > 0 and invuln_frames <= 0:
                player_hp -= dmg
                karma = min(float(player_max_hp), karma + 8.0)
                invuln_frames = int(round(10 / UT_SPEED))

        off_left = bullet["rect"].right < box_x - 80
        off_right = bullet["rect"].left > box_x + box_w + 80
        off_top = bullet["rect"].bottom < box_y - 80
        off_bottom = bullet["rect"].top > box_y + box_h + 80
        if off_left or off_right or off_top or off_bottom:
            bullets.remove(bullet)

    # KR drains after hit, and slowly chips HP like the original feel.
    if karma > 0 and player_hp > 1:
        karma = max(0.0, karma - 0.35 * UT_SPEED)
        player_hp = max(0.0, player_hp - 0.08 * UT_SPEED)

    player_hp = max(0.0, min(float(player_max_hp), player_hp))


def draw_dialog_box(text):
    dialog = pygame.Rect(12, 430, 776, 86)
    pygame.draw.rect(screen, WHITE, dialog, 4)
    pygame.draw.rect(screen, BLACK, dialog.inflate(-8, -8))
    rendered = font_med.render(text, True, WHITE)
    screen.blit(rendered, (dialog.x + 16, dialog.y + 26))


def draw_status_and_menu():
    hp_ratio = player_hp / player_max_hp
    kr_ratio = karma / player_max_hp

    stats_y = 526
    screen.blit(font_small.render(player_name, True, WHITE), (16, stats_y))
    screen.blit(font_small.render(f"LV {player_lv}", True, WHITE), (117, stats_y))
    screen.blit(font_small.render("HP", True, WHITE), (204, stats_y))

    bar_x, bar_y, bar_w, bar_h = 243, stats_y + 4, 160, 16
    pygame.draw.rect(screen, RED, (bar_x, bar_y, bar_w, bar_h))
    if hp_ratio > 0:
        pygame.draw.rect(screen, YELLOW, (bar_x, bar_y, int(bar_w * hp_ratio), bar_h))
    if kr_ratio > 0:
        pygame.draw.rect(screen, PURPLE, (bar_x, bar_y, int(bar_w * kr_ratio), bar_h), 2)

    hp_text = font_small.render(f"{int(player_hp):02d} / {player_max_hp}", True, WHITE)
    kr_text = font_small.render(f"KR {int(karma):02d} / {player_max_hp}", True, WHITE)
    screen.blit(hp_text, (410, stats_y))
    screen.blit(kr_text, (546, stats_y))

    if fight_phase == PHASE_PLAYER:
        turn_color, turn_text = YELLOW, "PLAYER TURN"
    elif fight_phase == PHASE_WAIT:
        turn_color, turn_text = WHITE, "SANS WAITING"
    else:
        turn_color, turn_text = BLUE, "SANS TURN"
    turn_label = font_small.render(turn_text, True, turn_color)
    screen.blit(turn_label, (640 - turn_label.get_width() // 2, stats_y))

    for index, button_surf in enumerate(menu_button_surfaces):
        rect = pygame.Rect(
            MENU_BX + index * (MENU_BW + MENU_GAP),
            MENU_BY,
            MENU_BW,
            MENU_BH,
        )
        screen.blit(button_surf, rect.topleft)
        if fight_phase == PHASE_PLAYER and index == selected_action:
            screen.blit(menu_cursor_surface, (rect.x + 8, rect.y + 9))


def draw_sans():
    screen.blit(sans_sprite_scaled, sans_sprite_scaled.get_rect(center=(WIDTH // 2, 96)))


def draw_fight_scene():
    pygame.draw.rect(screen, WHITE, (box_x, box_y, box_w, box_h), 4)
    pygame.draw.rect(screen, RED, soul_rect)

    for bullet in bullets:
        color = bullet["color"]
        rect = bullet["rect"]
        surf = get_bullet_surface(rect.width, rect.height, color, bullet["kind"])
        screen.blit(surf, rect.topleft)

    draw_gaster_blasters()


def draw_gaster_blasters():
    now = time.time()
    for blaster in gaster_blasters:
        start = blaster["origin"] + blaster["direction"] * 40
        end = start + blaster["direction"] * 1100
        if now >= blaster["warmup_end"]:
            if now <= blaster["beam_end"]:
                # Vanilla Undertale-style beam: dark outline + bright white core.
                pygame.draw.line(screen, (28, 28, 28), start, end, 24)
                pygame.draw.line(screen, WHITE, start, end, 16)
                pygame.draw.line(screen, (255, 255, 235), start, end, 7)
        else:
            # Warmup: pale targeting line (official telegraph feel).
            t = max(0.0, min(1.0, (now - (blaster["warmup_end"] - BLASTER_WARMUP)) / BLASTER_WARMUP))
            width = max(1, int(2 + t * 4))
            pygame.draw.line(screen, (255, 255, 210), start, end, width)
            if blaster["warmup_end"] - now <= BLASTER_CHARGE_FLASH:
                flash = int(200 + 55 * math.sin(now * 80))
                pygame.draw.line(screen, (flash, flash, 255), start, end, width + 5)

        face_index = blaster.get("face_index", 0)
        angle_key = int(round(blaster["angle"]))
        cache_key = (face_index, angle_key)
        sprite = blaster_rotation_cache.get(cache_key)
        if sprite is None:
            base_face = BLASTER_FACE_SURFACES[face_index % len(BLASTER_FACE_SURFACES)]
            sprite = pygame.transform.rotozoom(base_face, -angle_key, 1.0)
            blaster_rotation_cache[cache_key] = sprite
        rect = sprite.get_rect(center=(int(blaster["origin"].x), int(blaster["origin"].y)))
        screen.blit(sprite, rect)


def draw_main_menu():
    title = font_title.render("AC'S UNDERTALE", True, YELLOW)
    subtitle = font_med.render("LAST BREATH SANS FIGHT", True, WHITE)
    screen.blit(title, (WIDTH // 2 - title.get_width() // 2, 188))
    screen.blit(subtitle, (WIDTH // 2 - subtitle.get_width() // 2, 245))
    draw_dialog_box("* choose your route.")

    ticks = pygame.time.get_ticks()
    glow_index = (ticks // 70) % len(main_menu_glow_frames)
    bob = int(round(math.sin((2 * math.pi * ticks) / MAIN_MENU_PULSE_MS) * MAIN_MENU_SOUL_BOB_PX))

    for i, label in enumerate(MAIN_MENU_OPTIONS):
        x = WIDTH // 2 - MAIN_MENU_BW // 2
        y = MAIN_MENU_Y_START + i * (MAIN_MENU_BH + MAIN_MENU_GAP)
        if i == main_menu_selected:
            screen.blit(main_menu_glow_frames[glow_index], (x - 10, y - 10))
            screen.blit(main_menu_button_selected[i], (x, y))
        else:
            screen.blit(main_menu_button_idle[i], (x, y))
        if i == main_menu_selected:
            screen.blit(menu_cursor_surface, (x + 10, y + (MAIN_MENU_BH // 2 - 5) + bob))

    hint = font_small.render("Z/ENTER: SELECT    W/S OR UP/DOWN: MOVE", True, WHITE)
    screen.blit(hint, (WIDTH // 2 - hint.get_width() // 2, 387))


running = True
reset_run_state()
init_baked_ost()

while running:
    clock.tick(DISPLAY_FPS)
    screen.fill(BLACK)
    keys = pygame.key.get_pressed()
    prev_pos = soul_rect.topleft

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

        elif event.type == pygame.KEYDOWN:
            if game_state == STATE_INTRO:
                if event.key in (pygame.K_UP, pygame.K_w):
                    main_menu_selected = (main_menu_selected - 1) % len(MAIN_MENU_OPTIONS)
                elif event.key in (pygame.K_DOWN, pygame.K_s):
                    main_menu_selected = (main_menu_selected + 1) % len(MAIN_MENU_OPTIONS)
                elif event.key in (pygame.K_z, pygame.K_RETURN, pygame.K_SPACE):
                    if MAIN_MENU_OPTIONS[main_menu_selected] == "START":
                        game_state = STATE_DIALOGUE
                    else:
                        running = False
            elif game_state == STATE_DIALOGUE and event.key in (pygame.K_z, pygame.K_RETURN, pygame.K_SPACE):
                dialogue_index += 1
                if dialogue_index >= len(dialogue_lines):
                    game_state = STATE_FIGHT
                    start_player_turn()
            elif game_state == STATE_FIGHT and fight_phase == PHASE_PLAYER:
                if event.key == pygame.K_LEFT:
                    selected_action = (selected_action - 1) % len(ACTION_LABELS)
                elif event.key == pygame.K_RIGHT:
                    selected_action = (selected_action + 1) % len(ACTION_LABELS)
                elif event.key in (pygame.K_z, pygame.K_RETURN, pygame.K_SPACE):
                    action = ACTION_LABELS[selected_action]
                    if action == "FIGHT":
                        start_sans_wait("* You attack. Sans sidesteps.")
                    elif action == "ACT":
                        start_sans_wait("* You ACT. Sans smirks.")
                    elif action == "ITEM":
                        healed = min(12, player_max_hp - player_hp)
                        player_hp += healed
                        start_sans_wait(f"* You used an item. +{int(healed)} HP.")
                    elif action == "MERCY":
                        start_sans_wait("* You showed mercy. Sans refuses.")
            elif game_state == STATE_GAME_OVER and event.key == pygame.K_r:
                reset_run_state()

    if game_state == STATE_FIGHT:
        now = time.time()
        if fight_phase == PHASE_WAIT:
            remaining = max(0, int(round(sans_wait_duration - (now - phase_started_at))))
            fight_text = f"* Sans waits... {remaining}s"
            if now - phase_started_at >= sans_wait_duration:
                start_sans_attack()

        elif fight_phase == PHASE_ATTACK:
            if keys[pygame.K_LEFT]:
                soul_rect.x -= soul_speed
            if keys[pygame.K_RIGHT]:
                soul_rect.x += soul_speed
            if keys[pygame.K_UP]:
                soul_rect.y -= soul_speed
            if keys[pygame.K_DOWN]:
                soul_rect.y += soul_speed

            soul_rect.x = max(box_x + 5, min(soul_rect.x, box_x + box_w - soul_size - 5))
            soul_rect.y = max(box_y + 5, min(soul_rect.y, box_y + box_h - soul_size - 5))

            if now - last_attack_time >= ATTACK_COOLDOWN:
                spawn_attack(attack_order[attack_index])
                attack_index = (attack_index + 1) % len(attack_order)
                last_attack_time = now

            moved_this_frame = soul_rect.topleft != prev_pos
            update_attacks(moved_this_frame)
            update_gaster_blasters()

            if now - phase_started_at >= SANS_ATTACK_DURATION:
                start_player_turn()

        if player_hp <= 0:
            game_state = STATE_GAME_OVER

    if game_state == STATE_INTRO:
        draw_sans()
        draw_main_menu()

    elif game_state == STATE_DIALOGUE:
        draw_sans()
        draw_dialog_box("* " + dialogue_lines[dialogue_index])
        draw_status_and_menu()

    elif game_state == STATE_FIGHT:
        draw_sans()
        draw_fight_scene()
        draw_beam_flash_overlay()
        draw_dialog_box(fight_text)
        draw_status_and_menu()

    elif game_state == STATE_GAME_OVER:
        draw_sans()
        over = font_title.render("YOU DIED", True, RED)
        retry = font_med.render("Press R to reset timeline", True, WHITE)
        screen.blit(over, (WIDTH // 2 - over.get_width() // 2, 250))
        screen.blit(retry, (WIDTH // 2 - retry.get_width() // 2, 320))

    pygame.display.flip()

pygame.quit()
sys.exit()
