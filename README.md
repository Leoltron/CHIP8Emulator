# CHIP8
Автор: Пироговский Леонид

## Описание
Данная програмам является программным эмулятором компьютера CHIP-8

## Управление:
CHIP-8 использует для управления клавиатуру 4x4 в формате:

| 1 | 2 | 3 | C |
|---|---|---|---|
| 4 | 5 | 6 | D |
| 7 | 8 | 9 | E |
| A | 0 | B | F |

Программа использует, стоответственно, такие клавиши на клавиатуре:

| 1 | 2 | 3 | 4 |
|---|---|---|---|
| Q | W | E | R |
| A | S | D | F |
| Z | X | C | V |

## Требования
* PyQt5
* kivy версии 1.10 или выше (Только для звука)

## Состав
* Ядро эмулятора: 'emulator.py'
* Экран эмулятора: 'screen.py'
* Шрифты: 'font.py'
* Тесты: 'tests.py'

## Использование
main.py <Путь к программе> [--no-sound] [--no-delay]
* --no-sound - отключает использование звука
* --no-delay - отключает исскуственную задержку работы программы
