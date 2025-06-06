FROM alpine:latest

# Install the modprobe utility
RUN apk add --no-cache kmod


# Copy the startup script
COPY startup.sh ./startup.sh

RUN chmod +x ./startup.sh

# Run the startup script
CMD ["./startup.sh"]