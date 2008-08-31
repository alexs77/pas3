var Logger = Class.create({
    initialize: function(divId) {
        this.log = [];
        this.level = 0;
        if (divId == null) divId = "logging_window";
        this.divId = divId;
    },
    setLevel: function(level) {
        this.level = level;
        alert("set level!");
    },
    logMessage: function(message, level) {
        this.log.push(new Array(message, level));
        if (level == null) { level = 0; }
        if (level >= this.level) {
            var spanNode = document.createElement("span");
            $(spanNode).appendChild(document.createTextNode(message));
            $(spanNode).addClassName("log"+level);
            $(this.divId).appendChild(spanNode);
        }
    },
    DEBUG: 0,
    INFO: 10,
    WARN: 20,
    WARNING: 20,
    ERROR: 30,
    CRITICAL: 40,
    FATAL: 50,
    FAIL: 50
});

var logger = new Logger();
