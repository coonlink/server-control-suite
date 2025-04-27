#!/bin/bash

# Скрипт для мониторинга тяжелых процессов
# Используется в server_control_bot.py

# Базовая директория
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Проверка аргументов
ANALYZE_MODE=0
if [[ "$1" == "--analyze" ]]; then
    ANALYZE_MODE=1
fi

# Получение списка тяжелых процессов
get_heavy_processes() {
    echo "=== Тяжелые процессы по CPU ==="
    ps aux --sort=-%cpu | head -6
    
    echo -e "\n=== Тяжелые процессы по памяти ==="
    ps aux --sort=-%mem | head -6
}

# Анализ процессов
analyze_processes() {
    echo "=== Анализ тяжелых процессов ==="
    
    # Топ 5 процессов по CPU
    TOP_CPU_PROCESSES=$(ps aux --sort=-%cpu | head -6 | tail -5)
    
    # Топ 5 процессов по памяти
    TOP_MEM_PROCESSES=$(ps aux --sort=-%mem | head -6 | tail -5)
    
    # Вывод результатов
    echo "Топ процессы по CPU:"
    echo "$TOP_CPU_PROCESSES"
    
    echo -e "\nТоп процессы по памяти:"
    echo "$TOP_MEM_PROCESSES"
    
    # Проверка проблемных процессов
    echo -e "\nРекомендации по оптимизации:"
    CPU_HOGS=$(echo "$TOP_CPU_PROCESSES" | awk '{if ($3 > 90) print $11, $3"%"}')
    if [[ -n "$CPU_HOGS" ]]; then
        echo "Процессы с высоким потреблением CPU (>90%):"
        echo "$CPU_HOGS"
    fi
    
    MEM_HOGS=$(echo "$TOP_MEM_PROCESSES" | awk '{if ($4 > 30) print $11, $4"%"}')
    if [[ -n "$MEM_HOGS" ]]; then
        echo "Процессы с высоким потреблением памяти (>30%):"
        echo "$MEM_HOGS"
    fi
}

# Выполнение в зависимости от режима
if [[ $ANALYZE_MODE -eq 1 ]]; then
    analyze_processes
else
    get_heavy_processes
fi

exit 0 