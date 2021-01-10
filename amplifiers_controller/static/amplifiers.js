var ws = new WebSocket(`ws://${document.location.host}/ws`);

function validateKey(key, value, report) {
    if (key == 'input') {
        return (0 <= value) && (value <= 8);
    }
    if (key == 'reflected') {
        return value <= report.output - 15;
    }
    if (key == 'temperature') {
        return (0 <= value) && (value <= 80);
    }
    return true
}

ws.onmessage = function(event) {
    let data = JSON.parse(event.data);
    card = $(`.card[data-index=${data.index}]`);
    for (let [key, value] of Object.entries(data.report)) {
        card.find(`.${key}`).text(value);
        if (validateKey(key, value, data.report)) {
            card.find(`.${key}`).css('color', '');
            card.find(`.${key}`).css('font-weight', '');
        } else {
            card.find(`.${key}`).css('color', 'red');
            card.find(`.${key}`).css('font-weight', 'bold');
        }

    }
};

$("input[type=submit]").on("click", function (e) {
    if (!this.form.checkValidity()) {
        return true;
    }

    var url = "/configure/" + $(this).closest(".card")[0].dataset.index;
    $.ajax({
        type: "POST",
        url: url,
        data: $(this.parentNode).serialize(), // serializes the form's elements.
    });

    return false; // avoid to execute the actual submit of the form.
});