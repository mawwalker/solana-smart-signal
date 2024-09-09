FROM archlinux

RUN pacman -Syyu --noconfirm && pacman -S python python-pip --noconfirm

WORKDIR /app

COPY requirements.txt /app/

RUN pip install --no-cache-dir --break-system-packages -r requirements.txt

ENV TZ=Asia/Shanghai

COPY . /app/
CMD ["python", "app.py"]