FROM --platform=$TARGETPLATFORM debian:12

# Labels and Credits
LABEL \
    name="reNgine" \
    author="Yogesh Ojha <yogesh.ojha11@gmail.com>" \
    description="reNgine is a automated pipeline of recon process, useful for information gathering during web application penetration testing."

# Environment Variables
ENV DEBIAN_FRONTEND="noninteractive" \
    DATABASE="postgres"
ENV USERNAME="rengine"

RUN apt update -y && apt install -y      \
    build-essential     \
    zlib1g-dev          \
    libncurses5-dev     \
    libgdbm-dev         \
    libnss3-dev         \
    libssl-dev          \
    libreadline-dev     \
    libffi-dev          \
    libsqlite3-dev      \
    libbz2-dev          \
    wget                \
    libpcap-dev         \
    libpq-dev           \
    vim                 \
    xvfb                \
    git                 \
    unzip               \
    curl                \
    gettext             \
    nmap

ENV USERNAME="rengine"
RUN addgroup --gid 1000 --system $USERNAME && \
    mkdir -p /home/$USERNAME && \
    adduser --gid 1000 --system --shell /bin/false --disabled-password --uid 1000 --home /home/$USERNAME $USERNAME && \
    chown $USERNAME:$USERNAME /home/$USERNAME

RUN wget -q https://packages.mozilla.org/apt/repo-signing-key.gpg -O- | tee /etc/apt/keyrings/packages.mozilla.org.asc && \
    gpg -n -q --import --import-options import-show /etc/apt/keyrings/packages.mozilla.org.asc | awk '/pub/{getline; gsub(/^ +| +$/,""); print "\n"$0"\n"}' && \
    echo "deb [signed-by=/etc/apt/keyrings/packages.mozilla.org.asc] https://packages.mozilla.org/apt mozilla main" | tee -a /etc/apt/sources.list.d/mozilla.list && \
    echo '\
Package: *\
Pin: origin packages.mozilla.org\
Pin-Priority: 1000\
' | tee /etc/apt/preferences.d/mozilla && apt update -y && apt install -y firefox

RUN cd /root && wget https://www.python.org/ftp/python/3.10.0/Python-3.10.0.tgz && \
    tar -xvf Python-3.10.0.tgz && \
    rm Python-3.10.0.tgz && \
    cd Python-3.10.0 && \
   ./configure --enable-optimizations && \
    make -j4 && \
    make altinstall

# Download and install go 1.21.4
RUN wget https://golang.org/dl/go1.21.4.linux-amd64.tar.gz && \
    tar -xvf go1.21.4.linux-amd64.tar.gz && \
    rm go1.21.4.linux-amd64.tar.gz && \
    mv go /usr/local


USER $USERNAME
WORKDIR /home/$USERNAME

ENV TOOLPATH="/home/${USERNAME}/tools"
ENV WORDLISTPATH="/home/${USERNAME}/wordlists"
ENV PIPX_BIN_DIR="${TOOLPATH}/pipx"
ENV GOROOT="/usr/local/go"
ENV GOPATH="${TOOLPATH}/go"
ENV PATH="${PATH}:${GOROOT}/bin:${GOPATH}/bin:${PIPX_BIN_DIR}"

RUN mkdir -p $TOOLPATH/.github 

# Download Go packages
RUN printf "github.com/jaeles-project/gospider@v1.1.6\n \
    github.com/tomnomnom/gf@dcd4c361f9f5ba302294ed38b8ce278e8ba69006\n \
    github.com/tomnomnom/unfurl@v0.4.3\n \
    github.com/tomnomnom/waybackurls@v0.1.0\n \
    github.com/projectdiscovery/httpx/cmd/httpx@v1.6.0\n \
    github.com/projectdiscovery/subfinder/v2/cmd/subfinder@v2.6.6\n \
    github.com/projectdiscovery/nuclei/v3/cmd/nuclei@v3.2.6\n \
    github.com/projectdiscovery/naabu/v2/cmd/naabu@v2.3.0\n \
    github.com/hakluke/hakrawler@2.1\n \
    github.com/lc/gau/v2/cmd/gau@v2.2.1\n \
    github.com/owasp-amass/amass/v4/...@v4.2.0\n \
    github.com/ffuf/ffuf@v2.1.0\n \
    github.com/projectdiscovery/tlsx/cmd/tlsx@v1.1.6\n \
    github.com/hahwul/dalfox/v2@v2.9.2\n \
    github.com/projectdiscovery/katana/cmd/katana@v1.1.0\n \
    github.com/dwisiswant0/crlfuzz/cmd/crlfuzz@v1.4.1\n \
    github.com/sa7mon/s3scanner@c544f1cf00f70cae3f2155b24d336f515b7c598b\n" | xargs -L1 go install -ldflags="-s -w" -v || true && chmod 700 -R $GOPATH/pkg/* && rm -rf $GOPATH/pkg/* && rm -rf /home/$USERNAME/.cache/go-build/*

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

ENV PATH="/home/${USERNAME}/.local/bin:${PATH}"
RUN python3.10 -m pip install pipx && pipx ensurepath && printf "poetry\n\
    watchdog\n\
    https://github.com/aboul3la/Sublist3r/archive/refs/tags/1.1.zip\n\
    https://github.com/laramies/theHarvester/archive/refs/tags/4.6.0.zip\n\
    git+https://github.com/ncrocfer/whatportis@59a1718bf7c531f2a5a4e213cad0c047ce9c1c94\n\
    git+https://github.com/EnableSecurity/wafw00f@ae6a67f23c7bc7fd913d5a32d9b81efefefa2da4\n\
    h8mail\n" | xargs -L1 pipx install || true

# Install tools
RUN wget https://github.com/mozilla/geckodriver/releases/download/v0.32.0/geckodriver-v0.32.0-linux64.tar.gz && \
    tar -xvf geckodriver-v0.32.0-linux64.tar.gz && \
    rm geckodriver-v0.32.0-linux64.tar.gz && \
    mv geckodriver /home/$USERNAME/.local/bin && \
    cd $TOOLPATH/.github && git clone https://github.com/shmilylty/OneForAll.git && cd OneForAll && git reset --hard 9ecfda229199ebf30d9338f4c88cbeb7c40e16c2 && \
    cd $TOOLPATH/.github && git clone https://github.com/FortyNorthSecurity/EyeWitness.git && cd EyeWitness && git reset --hard ac0c7c0e2e11ff23af0a2cca708afd26ece94096 && \
    cd $TOOLPATH/.github && git clone https://github.com/UnaPibaGeek/ctfr.git && cd ctfr && git reset --hard 6c7fecdc6346c4f5322049e38f415d5bddaa420d && \
    cd $TOOLPATH/.github && git clone https://github.com/Tuhinshubhra/CMSeeK.git && cd CMSeeK && git reset --hard 20f9780d2e682874be959cfd487045c92e3c73f4 && \
    cd $TOOLPATH/.github && git clone https://github.com/GiJ03/Infoga.git && cd Infoga && git reset --hard 6834c6f863c2bdc92cc808934bb293571d1939c1 && \
    cd $TOOLPATH/.github && wget https://github.com/m3n0sd0n4ld/GooFuzz/releases/download/1.2.5/GooFuzz.v.1.2.5.zip && unzip GooFuzz.v.1.2.5.zip && rm GooFuzz.v.1.2.5.zip && mv GooFuzz* GooFuzz && echo "#!/bin/bash\n\nbash $TOOLPATH/.github/GooFuzz/GooFuzz \"\$@\"" > /home/$USERNAME/.local/bin/GooFuzz && chmod +x /home/$USERNAME/.local/bin/GooFuzz && \
    cd $TOOLPATH/.github && git clone https://github.com/1ndianl33t/Gf-Patterns && mkdir -p /home/$USERNAME/.gf/ && cp -r Gf-Patterns/*.json /home/$USERNAME/.gf/ && \
    cd $TOOLPATH/.github && git clone https://github.com/tomnomnom/gf.git && cp -r $TOOLPATH/.github/gf/examples/*.json /home/$USERNAME/.gf/ && \ 
    mkdir -p /home/$USERNAME/.nmap/ && cd /home/$USERNAME/.nmap/ && git clone https://github.com/scipag/vulscan.git && cd vulscan && git reset --hard 0c793c490455e7907a7c5cbaf3f7210e80d2ee57 && ln -s $TOOLPATH/.github/vulscan /home/$USERNAME/.nmap/vulscan && \
    mkdir -p $WORDLISTPATH && wget https://raw.githubusercontent.com/maurosoria/dirsearch/master/db/dicc.txt -O $WORDLISTPATH/dicc.txt && \
    wget https://raw.githubusercontent.com/danielmiessler/SecLists/master/Discovery/DNS/deepmagic.com-prefixes-top50000.txt -O $WORDLISTPATH/deepmagic.com-prefixes-top50000.txt && \
    mkdir -p /home/$USERNAME/nuclei-templates && wget https://raw.githubusercontent.com/NagliNagli/Shockwave-OSS/bd7445cd320a174d3073f0a61867a40849d28436/ssrf.yaml -O ~/nuclei-templates/ssrf_nagli.yaml && \
    mkdir -p /home/$USERNAME/results

COPY ./celery/*.toml /home/$USERNAME

# Install aliases for tools needing a pyproject.toml
RUN cd $TOOLPATH/.github/OneForAll && mv /home/$USERNAME/oneforall-pyproject.toml pyproject.toml && poetry env use python3.10 && poetry install --no-cache && echo "#!/bin/bash\n\npoetry -C $TOOLPATH/.github/OneForAll/ run python $TOOLPATH/.github/OneForAll/oneforall.py \"\$@\"" > /home/$USERNAME/.local/bin/oneforall && chmod +x /home/$USERNAME/.local/bin/oneforall && \
    cd $TOOLPATH/.github/ctfr && mv /home/$USERNAME/ctfr-pyproject.toml pyproject.toml && poetry env use python3.10 && poetry install --no-cache && echo "#!/bin/bash\n\npoetry -C $TOOLPATH/.github/ctfr/ run python $TOOLPATH/.github/ctfr/ctfr.py \"\$@\"" > /home/$USERNAME/.local/bin/ctfr && chmod +x /home/$USERNAME/.local/bin/ctfr && \
    cd $TOOLPATH/.github/EyeWitness/Python && mv /home/$USERNAME/eyewitness-pyproject.toml pyproject.toml && poetry env use python3.10 && poetry install --no-cache && echo "#!/bin/bash\n\npoetry -C $TOOLPATH/.github/EyeWitness/Python run python $TOOLPATH/.github/EyeWitness/Python/EyeWitness.py \"\$@\"" > /home/$USERNAME/.local/bin/EyeWitness && chmod +x /home/$USERNAME/.local/bin/EyeWitness && \
    cd $TOOLPATH/.github/CMSeeK && mv /home/$USERNAME/cmseek-pyproject.toml pyproject.toml && poetry env use python3.10 && poetry install --no-cache && echo "#!/bin/bash\n\npoetry -C $TOOLPATH/.github/CMSeeK/ run python $TOOLPATH/.github/CMSeeK/cmseek.py \"\$@\"" > /home/$USERNAME/.local/bin/cmseek && chmod +x /home/$USERNAME/.local/bin/cmseek && \
    cd $TOOLPATH/.github/Infoga && mv /home/$USERNAME/infoga-pyproject.toml pyproject.toml && poetry env use python3.10 && poetry install --no-cache && echo "#!/bin/bash\n\npoetry -C $TOOLPATH/.github/Infoga/ run python $TOOLPATH/.github/Infoga/infoga.py \"\$@\"" > /home/$USERNAME/.local/bin/infoga && chmod +x /home/$USERNAME/.local/bin/infoga && \
    cd /home/$USERNAME && poetry install

COPY ./celery/entrypoint.sh /entrypoint.sh
VOLUME /home/$USERNAME/rengine
VOLUME /home/$USERNAME/scan_results
WORKDIR /home/$USERNAME/rengine
ENTRYPOINT ["/entrypoint.sh"]