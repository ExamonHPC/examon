if [ -z "$JAVA_OPTS" ]; then
  JAVA_OPTS="-Xmx512m -Xms256m"
fi

JAVA_OPTS="$JAVA_OPTS --add-opens java.base/java.lang=ALL-UNNAMED"
JAVA_OPTS="$JAVA_OPTS --add-opens java.base/java.lang.reflect=ALL-UNNAMED"
JAVA_OPTS="$JAVA_OPTS --add-opens java.base/java.util=ALL-UNNAMED"

