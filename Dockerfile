FROM python:3.6-slim

# We'll install our python scripts in this directory of the image disk.
WORKDIR /scraper

# Copy the required files to the working directory.
ADD scraper.py requirements.txt /scraper/

# Install dependencies via pip.
RUN pip install -r requirements.txt

# Set the locale to FR as it is necessary to parse French dates.
RUN apt-get clean && apt-get -y update && apt-get install -y locales apt-utils && locale-gen fr_FR.UTF-8
RUN echo "Europe/Paris" > /etc/timezone && \
    dpkg-reconfigure -f noninteractive tzdata && \
    sed -i -e 's/# en_US.UTF-8 UTF-8/en_US.UTF-8 UTF-8/' /etc/locale.gen && \
    sed -i -e 's/# fr_FR.UTF-8 UTF-8/fr_FR.UTF-8 UTF-8/' /etc/locale.gen && \
    echo 'LANG="fr_FR.UTF-8"'>/etc/default/locale && \
    locale-gen fr fr_FR fr_FR.UTF-8 && \
    dpkg-reconfigure --frontend=noninteractive locales && \
    update-locale LANG=fr_FR.UTF-8

# Sensible default command, just a dry run.
CMD ["python", "/scraper/scraper.py", "--project_id=college-de-france", "--user_agent=https://github.com/attwad/cdf-scraper", "--dry_run"]
