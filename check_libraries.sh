#!/bin/bash

# Список библиотек для проверки
libraries=(
  "python3"
  "git"
  "curl"
  "wget"
  "nginx"
)

echo "Проверка установленных библиотек и их версий..."
echo ""

missing_libraries=()
update_libraries=()

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Функция для проверки наличия утилит
check_dependencies() {
  for cmd in curl jq wget; do
    if ! command -v "$cmd" &> /dev/null; then
      echo -e "${RED}⚠️ Для работы скрипта требуется $cmd. Установите его с помощью:${NC}"
      echo "sudo apt update && sudo apt install $cmd"
      exit 1
    fi
  done
}

# Функция получения доступной версии пакета из apt
get_available_apt_version() {
  local package=$1
  if command -v apt-cache &> /dev/null; then
    available_version=$(apt-cache policy "$package" | grep Candidate | awk '{print $2}')
    echo "$available_version"
  else
    echo "Н/Д"
  fi
}

# Функция получения самой свежей версии из официальных источников
get_latest_official_version() {
  local package=$1
  
  case "$package" in
    "python3")
      # Получаем последнюю версию Python с официального сайта
      latest_version=$(curl -s https://www.python.org/downloads/ | grep -o 'Python [0-9]\+\.[0-9]\+\.[0-9]\+' | head -1 | cut -d' ' -f2)
      echo "$latest_version"
      ;;
    "git")
      # Получаем последнюю версию Git с GitHub
      latest_version=$(curl -s https://api.github.com/repos/git/git/tags | jq -r '.[0].name' | sed 's/v//')
      echo "$latest_version"
      ;;
    "curl")
      # Получаем последнюю версию curl с официального репозитория
      latest_version=$(curl -s https://api.github.com/repos/curl/curl/releases/latest | jq -r '.tag_name' | sed 's/curl-//' | tr '_' '.')
      echo "$latest_version"
      ;;
    "wget")
      # Получаем последнюю версию wget с GNU 
      latest_version=$(curl -s https://ftp.gnu.org/gnu/wget/ | grep -o 'wget-[0-9]\+\.[0-9]\+\.[0-9]\+\.tar\.gz' | sort -V | tail -1 | grep -o '[0-9]\+\.[0-9]\+\.[0-9]\+')
      echo "$latest_version"
      ;;
    "nginx")
      # Получаем последнюю стабильную версию NGINX
      latest_version=$(curl -s https://nginx.org/en/download.html | grep -o 'nginx-[0-9]\+\.[0-9]\+\.[0-9]\+' | head -1 | cut -d'-' -f2)
      echo "$latest_version"
      ;;
    *)
      echo "Н/Д"
      ;;
  esac
}

# Функция получения информации о безопасности версии
get_security_info() {
  local package=$1
  local version=$2
  
  case "$package" in
    "python3")
      # Проверяем безопасность Python на основе информации из CVE
      security_url="https://www.cvedetails.com/vulnerability-list/vendor_id-10210/product_id-18230/Python-Python.html"
      security_info=$(curl -s "$security_url" | grep -i "$version" | wc -l)
      if [ "$security_info" -gt 0 ]; then
        echo -e "${YELLOW}⚠️ Для Python $version обнаружены потенциальные уязвимости. Подробнее: $security_url${NC}"
      else
        echo -e "${GREEN}✅ Версия Python $version не имеет известных уязвимостей.${NC}"
      fi
      ;;
    "git")
      security_url="https://github.com/git/git/security/advisories"
      echo -e "${BLUE}🔎 Информация о безопасности Git: $security_url${NC}"
      ;;
    "curl")
      security_url="https://curl.se/docs/security.html"
      echo -e "${BLUE}🔎 Информация о безопасности curl: $security_url${NC}"
      ;;
    "wget")
      security_url="https://www.cvedetails.com/vulnerability-list/vendor_id-72/product_id-361/GNU-Wget.html"
      echo -e "${BLUE}🔎 Информация о безопасности wget: $security_url${NC}"
      ;;
    "nginx")
      security_url="https://nginx.org/en/security_advisories.html"
      echo -e "${BLUE}🔎 Информация о безопасности NGINX: $security_url${NC}"
      ;;
    *)
      echo -e "${YELLOW}⚠️ Информация о безопасности для $package не найдена.${NC}"
      ;;
  esac
}

# Функция установки библиотеки
install_library() {
  local package=$1
  local version_type=$2  # apt, official
  
  echo -e "${BLUE}[*] Установка $package...${NC}"
  
  case "$version_type" in
    "apt")
      echo -e "${BLUE}[*] Установка из APT репозитория...${NC}"
      sudo apt update && sudo apt install -y "$package"
      return $?
      ;;
    "official")
      echo -e "${BLUE}[*] Установка последней официальной версии...${NC}"
      case "$package" in
        "python3")
          echo -e "${YELLOW}⚠️ Для установки последней версии Python рекомендуется использовать pyenv или conda.${NC}"
          read -p "Хотите установить pyenv? (y/n): " choice
          if [[ $choice == "y" || $choice == "Y" ]]; then
            curl -s https://pyenv.run | bash
          fi
          ;;
        "git")
          sudo add-apt-repository -y ppa:git-core/ppa && sudo apt update && sudo apt install -y git
          ;;
        "curl")
          # Собираем из исходников последнюю версию curl
          temp_dir=$(mktemp -d)
          latest_version=$(get_latest_official_version "curl")
          cd "$temp_dir" && \
          curl -O "https://curl.se/download/curl-${latest_version}.tar.gz" && \
          tar -xzf "curl-${latest_version}.tar.gz" && \
          cd "curl-${latest_version}" && \
          ./configure && make && sudo make install
          rm -rf "$temp_dir"
          ;;
        "wget")
          # Собираем из исходников последнюю версию wget
          temp_dir=$(mktemp -d)
          latest_version=$(get_latest_official_version "wget")
          cd "$temp_dir" && \
          curl -O "https://ftp.gnu.org/gnu/wget/wget-${latest_version}.tar.gz" && \
          tar -xzf "wget-${latest_version}.tar.gz" && \
          cd "wget-${latest_version}" && \
          ./configure && make && sudo make install
          rm -rf "$temp_dir"
          ;;
        "nginx")
          echo -e "${BLUE}[*] Добавление репозитория NGINX...${NC}"
          curl -s https://nginx.org/keys/nginx_signing.key | sudo apt-key add -
          echo "deb https://nginx.org/packages/mainline/ubuntu/ $(lsb_release -cs) nginx" | sudo tee /etc/apt/sources.list.d/nginx.list
          sudo apt update && sudo apt install -y nginx
          ;;
        *)
          echo -e "${RED}⚠️ Не поддерживается установка последней версии для $package${NC}"
          return 1
          ;;
      esac
      return $?
      ;;
    *)
      echo -e "${RED}⚠️ Неизвестный тип версии: $version_type${NC}"
      return 1
      ;;
  esac
}

# Функция получения установленной версии
get_installed_version() {
  local command=$1
  
  case "$command" in
    "python3")
      echo "$($command --version 2>&1 | awk '{print $2}')"
      ;;
    "git")
      echo "$($command --version | awk '{print $3}')"
      ;;
    "curl")
      echo "$($command --version | head -n 1 | awk '{print $2}')"
      ;;
    "wget")
      echo "$($command --version | head -n 1 | awk '{print $3}')"
      ;;
    "nginx")
      echo "$($command -v 2>&1 | head -n 1 | awk -F'/' '{print $2}')"
      ;;
    *)
      echo "$($command --version 2>&1 | head -n 1)"
      ;;
  esac
}

# Функция интерактивного меню
show_interactive_menu() {
  echo -e "\n${BLUE}======================================================${NC}"
  echo -e "${BLUE}| Интерактивное меню управления библиотеками         |${NC}"
  echo -e "${BLUE}======================================================${NC}"
  echo -e "${YELLOW}Выберите действие:${NC}"
  echo -e "1) Обновить все библиотеки через APT"
  echo -e "2) Установить библиотеку по вашему выбору"
  echo -e "3) Проверить информацию о безопасности библиотеки"
  echo -e "4) Выход"
  
  read -p "Ваш выбор: " menu_choice
  
  case $menu_choice in
    1)
      echo -e "${BLUE}[*] Обновление всех библиотек через APT...${NC}"
      sudo apt update && sudo apt upgrade -y ${update_libraries[*]}
      ;;
    2)
      echo -e "Доступные библиотеки:"
      for i in "${!libraries[@]}"; do
        echo "$((i+1))) ${libraries[$i]}"
      done
      
      read -p "Выберите номер библиотеки для установки: " lib_num
      if [[ $lib_num -gt 0 && $lib_num -le ${#libraries[@]} ]]; then
        selected_lib=${libraries[$((lib_num-1))]}
        echo -e "Выбрана библиотека: $selected_lib"
        echo -e "1) Установить из APT"
        echo -e "2) Установить последнюю официальную версию"
        
        read -p "Выберите вариант установки: " install_choice
        case $install_choice in
          1)
            install_library "$selected_lib" "apt"
            ;;
          2)
            install_library "$selected_lib" "official"
            ;;
          *)
            echo -e "${RED}⚠️ Неверный выбор!${NC}"
            ;;
        esac
      else
        echo -e "${RED}⚠️ Неверный номер библиотеки!${NC}"
      fi
      ;;
    3)
      echo -e "Доступные библиотеки:"
      for i in "${!libraries[@]}"; do
        echo "$((i+1))) ${libraries[$i]}"
      done
      
      read -p "Выберите номер библиотеки для проверки безопасности: " lib_num
      if [[ $lib_num -gt 0 && $lib_num -le ${#libraries[@]} ]]; then
        selected_lib=${libraries[$((lib_num-1))]}
        if command -v "$selected_lib" &> /dev/null; then
          installed_version=$(get_installed_version "$selected_lib")
          get_security_info "$selected_lib" "$installed_version"
        else
          echo -e "${RED}⚠️ Библиотека $selected_lib не установлена!${NC}"
        fi
      else
        echo -e "${RED}⚠️ Неверный номер библиотеки!${NC}"
      fi
      ;;
    4)
      echo -e "${GREEN}До свидания!${NC}"
      exit 0
      ;;
    *)
      echo -e "${RED}⚠️ Неверный выбор!${NC}"
      ;;
  esac
}

# Проверяем наличие необходимых утилит
check_dependencies

# Проверка каждой библиотеки
for lib in "${libraries[@]}"; do
  if command -v "$lib" &> /dev/null; then
    installed_version=$(get_installed_version "$lib")
    apt_version=$(get_available_apt_version "$lib")
    latest_version=$(get_latest_official_version "$lib")
    
    echo -e "${GREEN}✅ $lib установлен (путь: $(command -v "$lib"))${NC}"
    echo "   Установленная версия: $installed_version"
    echo "   Доступная версия в APT: $apt_version"
    echo "   Последняя официальная версия: $latest_version"
    
    # Проверка необходимости обновления через APT
    if [ "$installed_version" != "$apt_version" ] && [ "$apt_version" != "Н/Д" ]; then
      echo -e "   ${YELLOW}⚠️ Доступно обновление через APT!${NC}"
      update_libraries+=("$lib")
    fi
    
    # Проверка наличия более новой версии в официальных источниках
    if [ "$installed_version" != "$latest_version" ] && [ "$latest_version" != "Н/Д" ] && [ "$latest_version" != "" ]; then
      echo -e "   ${BLUE}🔄 Доступна новая официальная версия!${NC}"
    fi
    
    # Получаем информацию о безопасности
    get_security_info "$lib" "$installed_version"
    
    echo ""
  else
    echo -e "${RED}❌ $lib НЕ установлен${NC}"
    missing_libraries+=("$lib")
    
    # Получить информацию о последней версии
    latest_version=$(get_latest_official_version "$lib")
    echo "   Последняя официальная версия: $latest_version"
    echo ""
  fi
done

# Вывод информации о недостающих библиотеках
if [ ${#missing_libraries[@]} -eq 0 ]; then
  echo -e "${GREEN}Все необходимые библиотеки установлены.${NC}"
else
  echo -e "${YELLOW}Необходимо установить следующие библиотеки:${NC}"
  for lib in "${missing_libraries[@]}"; do
    echo "  - $lib"
  done
  
  echo ""
  echo -e "${BLUE}Вы можете установить их с помощью команды:${NC}"
  echo "sudo apt update && sudo apt install ${missing_libraries[*]}"
fi

# Вывод информации о доступных обновлениях
if [ ${#update_libraries[@]} -gt 0 ]; then
  echo ""
  echo -e "${YELLOW}Доступны обновления через APT для следующих библиотек:${NC}"
  for lib in "${update_libraries[@]}"; do
    echo "  - $lib"
  done
  
  echo ""
  echo -e "${BLUE}Вы можете обновить их с помощью команды:${NC}"
  echo "sudo apt update && sudo apt upgrade ${update_libraries[*]}"
  echo ""
  echo -e "${YELLOW}Примечание: Если вы хотите установить самые последние официальные версии,${NC}"
  echo -e "${YELLOW}возможно, потребуется использовать PPA, snap или собрать из исходников.${NC}"
fi

# Показываем интерактивное меню
show_interactive_menu 