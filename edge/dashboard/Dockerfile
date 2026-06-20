FROM nginx:alpine

# Copy the static web dashboard files to the Nginx HTML root directory
COPY index.html /usr/share/nginx/html/
COPY styles.css /usr/share/nginx/html/
COPY app.js /usr/share/nginx/html/
COPY favicon.png /usr/share/nginx/html/
COPY icon_192.png /usr/share/nginx/html/
COPY icon_512.png /usr/share/nginx/html/

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
