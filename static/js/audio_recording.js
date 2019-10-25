var reco = null;

navigator.getUserMedia = (navigator.getUserMedia ||
    navigator.webkitGetUserMedia ||
    navigator.mozGetUserMedia ||
    navigator.msGetUserMedia);

navigator.getUserMedia({audio: true}, create_stream, function (err) {
    console.log(err)
});

function create_stream(user_media) {
    var audio_context = new AudioContext();
    var stream_input = audio_context.createMediaStreamSource(user_media);
    reco = new Recorder(stream_input);
}


function start_reco() {
    console.log('start recording')
    $("#audio_error").hide()
    $("#audio_ok").hide()
    $("#audio_processing").hide()
    $("#start_record_button").hide();
    $("#stop_record_button").show();
    reco.record();
}

function stop_reco() {
    reco.stop();
    $("#start_record_button").show();

    $("#stop_record_button").hide();
    console.log('stop recording')
}

function get_audio() {
    console.log('submitting audio')
    $("#audio_processing").show()
    reco.exportWAV(function (wav_file) {
        // wav_file = Blob对象 file对象
        // ws.send(wav_file);
        var formdata = new FormData();
        formdata.append("record", wav_file);

        // formdata.append("sender", toy_id);
        // formdata.append("to_user", document.getElementById("from_user").innerText);
        $.ajax({
            url: "/toy_uploader",  // ⚠️
            type: 'post',
            processData: false,
            contentType: false,
            data: formdata,
            dataType: 'json',
            success: function (data) {
                console.log(data);
                $("#audio_processing").hide()
                if (data.err_msg!="success."){
                    $("#audio_error").text(data.err_msg)
                    $("#audio_error").show()
                    $("#audio_ok").hide()

                }else {
                    $("#searchinput").val(data.result[0])
                    $("#audio_error").hide()
                    $("#audio_ok").show()
                }
            }
        })
    })
    reco.clear();
}